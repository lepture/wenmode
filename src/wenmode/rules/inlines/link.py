from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Break, InlineCode, Node, Parent, Text
from wenmode.nodes import Image as ImageNode
from wenmode.nodes import Link as LinkNode
from wenmode.state import BlockState, StateKey
from wenmode.utils import is_escaped, normalize_label_text, normalize_uri_text

from ..base import InlineRule
from ..references import ReferenceTransform, resolve_state_reference
from .html import EMAIL_RE, HTML_RE, URI_RE

if TYPE_CHECKING:
    from wenmode.parser import Parser


ANGLE_SPAN_RE = re.compile(rf'{URI_RE}|{EMAIL_RE}|{HTML_RE}')
ClosingBracketCache = dict[int, tuple[str, dict[int, int]]]
CLOSING_BRACKET_CACHE = StateKey[ClosingBracketCache]('wenmode.inline.closing_brackets', lambda: {})


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
        return ImageNode(
            url=url, alt=plain_text(parser.parse_inlines(label, state, source=label_source)), title=title
        ), end


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
        parsed = parse_link_or_image(parser, text, match.start(), image=False, state=state, references=self.references)
        if parsed is None:
            return None, match.start()

        label, url, title, end, label_start, label_end = parsed
        label_source = parser.inline_source(text, state, label_start, label_end)
        return LinkNode(url=url, title=title, children=parser.parse_inlines(label, state, source=label_source)), end


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

    label = text[label_start:label_end]
    after_label = label_end + 1
    if not image and label_contains_link(parser, label, state):
        return None

    direct = parse_direct_destination(text, after_label)
    if direct is not None:
        url, title, end = direct
        return label, url, title, end, label_start, label_end
    if not references:
        return None

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


def label_contains_link(parser: Parser, label: str, state: BlockState) -> bool:
    if '[' not in label:
        return False
    return any(contains_link(node) for node in parser.parse_inlines(label, state))


def contains_link(node: Node) -> bool:
    if isinstance(node, LinkNode):
        return True
    if isinstance(node, Parent):
        return any(contains_link(child) for child in node.children)
    return False


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
        end = text.find('>', start + 1)
        if end == -1 or '\n' in text[start + 1 : end] or '\\' in text[start + 1 : end]:
            return None, start
        return text[start + 1 : end], end + 1

    chars: list[str] = []
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char in ' \t\r\n':
            break
        if char == '\\' and index + 1 < len(text):
            chars.append(text[index : index + 2])
            index += 2
            continue
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 0:
                break
            depth -= 1
        chars.append(char)
        index += 1

    return ''.join(chars), index


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
    marker = text[start:end]
    closer = re.search(rf'(?<!`){re.escape(marker)}(?!`)', text[end:])
    if closer is None:
        return None
    return end + closer.start() + len(marker)
