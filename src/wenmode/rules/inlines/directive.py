from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node
from wenmode.nodes import Text as TextNode
from wenmode.nodes import TextDirective as TextDirectiveNode

from ..._parser.source import SourceMap
from ..._parser.state import BlockState
from ..._parser.store import StateKey
from ..base import InlineRule
from ..directives import parse_attributes

if TYPE_CHECKING:
    from wenmode.parser import Parser


NAME_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]*')
DirectiveBracketCache = dict[int, tuple[str, dict[int, int], dict[int, int]]]
DIRECTIVE_BRACKET_CACHE = StateKey[DirectiveBracketCache]('wenmode.inline.directive_brackets', lambda: {})
TEXT_DIRECTIVE_DEPTH = StateKey[int]('wenmode.inline.text_directive_depth', lambda: 0)


class TextDirective(InlineRule):
    """Parse mdast-style text directives such as ``:name[label]``.

    Markdown syntax:

    .. code-block:: markdown

       :abbr[HTML]{title="HyperText Markup Language"}
    """

    name = 'text_directive'
    pattern = r':(?=[A-Za-z])'
    opener = ':'

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        if start + 1 >= len(text) or text[start] != ':' or not text[start + 1].isascii() or not text[start + 1].isalpha():
            return None, start
        parsed = parse_text_directive_head(text, start + 1, state)
        if parsed is None:
            return None, start

        name, label, attributes, end, label_start, label_end = parsed
        if label is not None and label_start is not None and label_end is not None:
            children = parse_text_directive_children(
                parser, label, state, parser.inline_source(text, state, label_start, label_end)
            )
        else:
            children = []
        return TextDirectiveNode(name=name, attributes=attributes, children=children), end


def parse_text_directive_children(
    parser: Parser, label: str, state: BlockState, source: SourceMap | None
) -> list[Node]:
    depth = state.store.get(TEXT_DIRECTIVE_DEPTH)
    if depth >= parser.max_container_depth:
        return [TextNode(value=label)]

    state.store.set(TEXT_DIRECTIVE_DEPTH, depth + 1)
    try:
        return parser.parse_inlines(label, state, source=source)
    finally:
        state.store.set(TEXT_DIRECTIVE_DEPTH, depth)


def parse_text_directive_head(
    text: str, start: int, state: BlockState
) -> tuple[str, str | None, dict[str, str] | None, int, int | None, int | None] | None:
    match = NAME_RE.match(text, start)
    if match is None:
        return None

    name = match.group(0)
    index = match.end()
    label: str | None = None
    label_start: int | None = None
    label_end: int | None = None
    attributes: dict[str, str] | None = None
    square_pairs, brace_pairs = directive_bracket_pairs(text, state)

    if index < len(text) and text[index] == '[':
        square_end = square_pairs.get(index)
        if square_end is None:
            return None
        label = text[index + 1 : square_end]
        label_start = index + 1
        label_end = square_end
        index = square_end + 1

    if index < len(text) and text[index] == '{':
        brace_end = brace_pairs.get(index)
        if brace_end is None:
            return None
        attributes = parse_attributes(text[index + 1 : brace_end])
        index = brace_end + 1

    return name, label, attributes, index, label_start, label_end


def directive_bracket_pairs(text: str, state: BlockState) -> tuple[dict[int, int], dict[int, int]]:
    cache = state.store.get(DIRECTIVE_BRACKET_CACHE)
    key = id(text)
    cached = cache.get(key)
    if cached is not None and cached[0] is text:
        return cached[1], cached[2]

    square_pairs, brace_pairs = build_directive_bracket_pairs(text)
    cache[key] = (text, square_pairs, brace_pairs)
    return square_pairs, brace_pairs


def build_directive_bracket_pairs(text: str) -> tuple[dict[int, int], dict[int, int]]:
    square_pairs: dict[int, int] = {}
    brace_pairs: dict[int, int] = {}
    square_stack: list[int] = []
    brace_stack: list[int] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char == '\\':
            index += 2
            continue
        if char == '[':
            square_stack.append(index)
        elif char == ']' and square_stack:
            square_pairs[square_stack.pop()] = index
        elif char == '{':
            brace_stack.append(index)
        elif char == '}' and brace_stack:
            brace_pairs[brace_stack.pop()] = index
        index += 1
    return square_pairs, brace_pairs
