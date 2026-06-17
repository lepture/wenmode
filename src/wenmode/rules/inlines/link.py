from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Break, InlineCode, Node, Parent, Text
from wenmode.nodes import Image as ImageNode
from wenmode.nodes import Link as LinkNode
from wenmode.state import BlockState
from wenmode.utils import normalize_label, normalize_label_text, normalize_uri_text

from ..base import InlineRule
from ..references import ReferenceTransform
from .html import EMAIL_RE, HTML_RE, URI_RE

if TYPE_CHECKING:
    from wenmode.parser import Parser


ANGLE_SPAN_RE = re.compile(rf'{URI_RE}|{EMAIL_RE}|{HTML_RE}')
ClosingBracketCache = dict[int, tuple[str, dict[int, int]]]


class Image(InlineRule):
    def __init__(self, references: bool = True) -> None:
        super().__init__('image', r'!\[', '!')
        self.references = references
        self.root_transforms = [ReferenceTransform()] if references else []

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        parsed = parse_link_or_image(parser, text, match.start(), image=True, state=state, references=self.references)
        if parsed is None:
            return None, match.start()

        label, url, title, end = parsed
        return ImageNode(url=url, alt=plain_text(parser.parse_inlines(label, state)), title=title), end


class Link(InlineRule):
    def __init__(self, references: bool = True) -> None:
        super().__init__('link', r'\[', '[')
        self.references = references
        self.root_transforms = [ReferenceTransform()] if references else []

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        if match.start() > 0 and text[match.start() - 1] == '!' and not is_escaped(text, match.start() - 1):
            return None, match.start()
        parsed = parse_link_or_image(parser, text, match.start(), image=False, state=state, references=self.references)
        if parsed is None:
            return None, match.start()

        label, url, title, end = parsed
        return LinkNode(url=url, title=title, children=parser.parse_inlines(label, state)), end


def normalize_optional_text(value: str | None) -> str | None:
    return normalize_label_text(value) if value is not None else None


def parse_link_or_image(
    parser: Parser, text: str, start: int, image: bool, state: BlockState | None, references: bool = True
) -> tuple[str, str, str | None, int] | None:
    bracket_cache = closing_bracket_cache(state)
    label_start = start + 2 if image else start + 1
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
        return label, url, title, end
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

    if state:
        reference = state.get_reference(normalize_label(reference_label))
        if reference is not None:
            return label, reference.url, reference.title, end
    return None


def closing_bracket_cache(state: BlockState | None) -> ClosingBracketCache | None:
    if state is None:
        return None
    return cast(ClosingBracketCache, state.inline_cache.setdefault('closing_brackets', {}))


def find_closing_bracket(text: str, start: int, cache: ClosingBracketCache | None = None) -> int | None:
    if start > 0 and text[start - 1] == '[':
        return closing_bracket_map(text, cache).get(start)
    return find_closing_bracket_uncached(text, start)


def closing_bracket_map(text: str, cache: ClosingBracketCache | None) -> dict[int, int]:
    if cache is None:
        return build_closing_bracket_map(text)

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


def find_closing_bracket_uncached(text: str, start: int) -> int | None:
    depth = 0
    index = start
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
            depth += 1
        elif char == ']':
            if depth == 0:
                return index
            depth -= 1
        index += 1
    return None


def label_contains_link(parser: Parser, label: str, state: BlockState | None) -> bool:
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


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == '\\':
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def find_code_span_end(text: str, start: int) -> int | None:
    end = start
    while end < len(text) and text[end] == '`':
        end += 1
    marker = text[start:end]
    closer = re.search(rf'(?<!`){re.escape(marker)}(?!`)', text[end:])
    if closer is None:
        return None
    return end + closer.start() + len(marker)
