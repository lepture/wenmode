from __future__ import annotations

import re
from bisect import bisect_left
from typing import TYPE_CHECKING

from wenmode.nodes import Break, InlineCode, Node, Parent, Text
from wenmode.nodes import Image as ImageNode
from wenmode.nodes import Link as LinkNode
from wenmode.utils import is_escaped, normalize_label_text, normalize_uri_text
from wenmode.utils.text import parse_angle_destination, parse_bare_destination

from ..._parser.source import SourceMap
from ..._parser.state import BlockState
from ..._parser.store import StateKey
from ..base import InlineRule
from ..references import REFERENCES_KEY, ReferenceTransform, resolve_state_reference
from .code import find_matching_backtick_run
from .html import EMAIL_RE, HTML_RE, URI_RE

if TYPE_CHECKING:
    from wenmode.parser import Parser


ANGLE_SPAN_RE = re.compile(rf'{URI_RE}|{EMAIL_RE}|{HTML_RE}')
ClosingBracketCache = dict[int, tuple[str, dict[int, int]]]
LinkContainmentCache = dict[tuple[int, bool, int, int], tuple[str, list[int], list[int]]]
CLOSING_BRACKET_CACHE = StateKey[ClosingBracketCache]('wenmode.inline.closing_brackets', lambda: {})
LINK_CONTAINMENT_CACHE = StateKey[LinkContainmentCache]('wenmode.inline.link_containment', lambda: {})
IN_LINK_DEPTH = StateKey[int]('wenmode.inline.in_link_depth', lambda: 0)
IMAGE_ALT_DEPTH = StateKey[int]('wenmode.inline.image_alt_depth', lambda: 0)


class Image(InlineRule):
    """Parse inline and reference-style images.

    Markdown syntax:

    .. code-block:: markdown

       ![alt](/image.png)

    :param references: Enable reference-style images and reference definitions.
    """

    name = 'image'
    pattern = r'!\['
    trigger_chars = '!'

    def __init__(self, references: bool = True) -> None:
        super().__init__()
        self.references = references
        if references:
            self.root_transforms = [ReferenceTransform()]
        else:
            self.root_transforms = []

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        parsed = parse_link_or_image(parser, text, match.start(), image=True, state=state, references=self.references)
        if parsed is None:
            return None, match.start()

        label, url, title, end, label_start, label_end = parsed
        label_source = parser.inline_source(text, state, label_start, label_end)
        return ImageNode(url=url, alt=parse_image_alt(parser, label, state, label_source), title=title), end


class Link(InlineRule):
    """Parse inline and reference-style links.

    Markdown syntax:

    .. code-block:: markdown

       [label](https://example.com)

    :param references: Enable reference-style links and reference definitions.
    """

    name = 'link'
    pattern = r'\['
    trigger_chars = '['

    def __init__(self, references: bool = True) -> None:
        super().__init__()
        self.references = references
        if references:
            self.root_transforms = [ReferenceTransform()]
        else:
            self.root_transforms = []

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        if match.start() > 0 and text[match.start() - 1] == '!' and not is_escaped(text, match.start() - 1):
            return None, match.start()
        if state.store.get(IN_LINK_DEPTH) > 0:
            return None, match.start()
        parsed = parse_link_or_image(parser, text, match.start(), image=False, state=state, references=self.references)
        if parsed is None:
            return None, match.start()

        label, url, title, end, label_start, label_end = parsed
        label_source = parser.inline_source(text, state, label_start, label_end)
        return LinkNode(url=url, title=title, children=parse_link_children(parser, label, state, label_source)), end


def parse_link_children(parser: Parser, label: str, state: BlockState, source: SourceMap | None) -> list[Node]:
    in_link = state.store.get(IN_LINK_DEPTH)
    state.store.set(IN_LINK_DEPTH, in_link + 1)
    try:
        return parser.parse_inlines(label, state, source=source)
    finally:
        state.store.set(IN_LINK_DEPTH, in_link)


def parse_image_alt(parser: Parser, label: str, state: BlockState, source: SourceMap | None) -> str:
    depth = state.store.get(IMAGE_ALT_DEPTH)
    if depth >= parser.max_container_depth:
        return label

    state.store.set(IMAGE_ALT_DEPTH, depth + 1)
    try:
        return plain_text(parser.parse_inlines(label, state, source=source))
    finally:
        state.store.set(IMAGE_ALT_DEPTH, depth)


def parse_link_or_image(
    parser: Parser, text: str, start: int, image: bool, state: BlockState, references: bool = True
) -> tuple[str, str, str | None, int, int, int] | None:
    bracket_cache = closing_bracket_cache(state)
    if image:
        label_start = start + 2
    else:
        label_start = start + 1
    label_end = find_closing_bracket(text, label_start, bracket_cache)
    if label_end is None:
        return None

    after_label = label_end + 1

    direct = parse_direct_destination(text, after_label)
    if direct is not None:
        if not image and label_contains_link(text, label_start, label_end, state, references):
            return None
        url, title, end = direct
        return text[label_start:label_end], url, title, end, label_start, label_end
    if not references:
        return None

    label = text[label_start:label_end]
    reference_label = label
    end = after_label
    if after_label < len(text) and text[after_label] == '[':
        ref_end = find_closing_bracket(text, after_label + 1, bracket_cache)
        if ref_end is None:
            return None
        explicit = text[after_label + 1 : ref_end]
        if invalid_reference_label(explicit):
            return None
        if explicit:
            reference_label = explicit
        end = ref_end + 1
    elif invalid_reference_label(reference_label):
        return None

    reference = resolve_state_reference(state, reference_label)
    if reference is not None:
        if not image and label_contains_link(text, label_start, label_end, state, references):
            return None
        return label, reference.url, reference.title, end, label_start, label_end
    return None


def closing_bracket_cache(state: BlockState) -> ClosingBracketCache:
    return state.store.get(CLOSING_BRACKET_CACHE)


def find_closing_bracket(text: str, start: int, cache: ClosingBracketCache) -> int | None:
    return closing_bracket_map(text, cache).get(start)


def closing_bracket_map(text: str, cache: ClosingBracketCache) -> dict[int, int]:
    key = id(text)
    cached = cache.get(key)
    if cached is not None and cached[0] is text:
        return cached[1]

    pairs = build_closing_bracket_map(text)
    cache[key] = (text, pairs)
    return pairs


def build_closing_bracket_map(text: str) -> dict[int, int]:
    pairs: dict[int, int] = {}
    stack: list[int] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '\\':
            index += 2
            continue
        if char == '`':
            code_end = find_code_span_end(text, index)
            if code_end is not None:
                index = code_end
                continue
            while index < len(text) and text[index] == '`':
                index += 1
            continue
        if char == '<':
            angle_end = find_angle_span_end(text, index)
            if angle_end is not None:
                index = angle_end
                continue
        if char == '[':
            stack.append(index)
        elif char == ']' and stack:
            pairs[stack.pop() + 1] = index
        index += 1
    return pairs


def label_contains_link(text: str, label_start: int, label_end: int, state: BlockState, references: bool) -> bool:
    bracket_cache = closing_bracket_cache(state)
    pairs = closing_bracket_map(text, bracket_cache)
    starts, suffix_min_ends = link_containment_index(text, state, pairs, references)
    index = bisect_left(starts, label_start)
    return index < len(starts) and starts[index] < label_end and suffix_min_ends[index] <= label_end


def link_containment_index(
    text: str, state: BlockState, pairs: dict[int, int], references: bool
) -> tuple[list[int], list[int]]:
    reference_cache = state.store.get(REFERENCES_KEY)
    cache_key = (id(text), references, id(reference_cache), len(reference_cache))
    cache = state.store.get(LINK_CONTAINMENT_CACHE)
    cached = cache.get(cache_key)
    if cached is not None and cached[0] is text:
        return cached[1], cached[2]

    ranges: list[tuple[int, int]] = []
    for nested_label_start, nested_label_end in pairs.items():
        opener = nested_label_start - 1
        if is_image_label(text, opener):
            continue
        nested_end = link_destination_or_reference_end(
            text, nested_label_start, nested_label_end, state, pairs, references
        )
        if nested_end is not None:
            ranges.append((opener, nested_end))

    ranges.sort()
    starts = [start for start, _end in ranges]
    suffix_min_ends = [end for _start, end in ranges]
    for index in range(len(suffix_min_ends) - 2, -1, -1):
        suffix_min_ends[index] = min(suffix_min_ends[index], suffix_min_ends[index + 1])
    cache[cache_key] = (text, starts, suffix_min_ends)
    return starts, suffix_min_ends


def is_image_label(text: str, start: int) -> bool:
    return start > 0 and text[start - 1] == '!' and not is_escaped(text, start - 1)


def link_destination_or_reference_end(
    text: str, label_start: int, label_end: int, state: BlockState, pairs: dict[int, int], references: bool
) -> int | None:
    after_label = label_end + 1
    direct = parse_direct_destination(text, after_label)
    if direct is not None:
        return direct[2]
    if not references or not state.store.get(REFERENCES_KEY):
        return None
    if after_label < len(text) and text[after_label] == '[':
        ref_end = pairs.get(after_label + 1)
        if ref_end is None:
            return None
        explicit = text[after_label + 1 : ref_end]
        if invalid_reference_label(explicit):
            return None
        reference_label = explicit or text[label_start:label_end]
        if resolve_state_reference(state, reference_label) is None:
            return None
        return ref_end + 1
    reference_label = text[label_start:label_end]
    if invalid_reference_label(reference_label) or resolve_state_reference(state, reference_label) is None:
        return None
    return after_label


def invalid_reference_label(label: str) -> bool:
    index = 0
    while index < len(label):
        if label[index] != '\\':
            index += 1
            continue
        if index + 1 >= len(label) or label[index + 1] not in '[]\\':
            return True
        index += 2
    return False


def find_angle_span_end(text: str, start: int) -> int | None:
    match = ANGLE_SPAN_RE.match(text, start)
    if match is None:
        return None
    return match.end()


def parse_direct_destination(text: str, start: int) -> tuple[str, str | None, int] | None:
    if start >= len(text) or text[start] != '(':
        return None
    index = skip_link_spaces(text, start + 1)
    destination, index = parse_destination(text, index)
    if destination is None:
        return None

    after_destination = skip_link_spaces(text, index)
    title: str | None = None
    parsed_title = parse_title(text, after_destination)
    if parsed_title is not None:
        title, after_destination = parsed_title
        after_destination = skip_link_spaces(text, after_destination)

    if after_destination >= len(text) or text[after_destination] != ')':
        return None
    return normalize_uri_text(destination), title, after_destination + 1


def skip_link_spaces(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index] in ' \t\r\n':
        index += 1
    return index


def parse_destination(text: str, start: int) -> tuple[str | None, int]:
    if start < len(text) and text[start] == '<':
        return parse_angle_destination(text, start)
    return parse_bare_destination(text, start)


def parse_title(text: str, start: int) -> tuple[str, int] | None:
    if start >= len(text):
        return None
    opener = text[start]
    closer = {'"': '"', "'": "'", '(': ')'}.get(opener)
    if closer is None:
        return None
    index = start + 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == closer:
            return normalize_label_text(text[start + 1 : index]), index + 1
        index += 1
    return None


def plain_text(nodes: list[Node]) -> str:
    values: list[str] = []
    for node in nodes:
        if isinstance(node, Text | InlineCode):
            values.append(node.value)
        elif isinstance(node, ImageNode):
            values.append(node.alt)
        elif isinstance(node, Break):
            values.append('\n')
        elif isinstance(node, Parent):
            values.append(plain_text(node.children))
    return ''.join(values)


def find_code_span_end(text: str, start: int) -> int | None:
    end = start
    while end < len(text) and text[end] == '`':
        end += 1
    marker_length = end - start
    closer = find_matching_backtick_run(text, end, marker_length)
    if closer is None:
        return None
    return closer + marker_length
