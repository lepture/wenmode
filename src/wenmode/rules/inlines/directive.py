from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node
from wenmode.nodes import TextDirective as TextDirectiveNode
from wenmode.state import BlockState, StateKey

from ..base import InlineRule
from ..directives import parse_attributes, parse_directive_head

if TYPE_CHECKING:
    from wenmode.parser import Parser


NAME_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]*')
DirectiveBracketCache = dict[int, tuple[str, dict[int, int], dict[int, int]]]
DIRECTIVE_BRACKET_CACHE = StateKey[DirectiveBracketCache]('wenmode.inline.directive_brackets', lambda: {})


class TextDirective(InlineRule):
    """Parse mdast-style text directives such as ``:name[label]``.

    Markdown syntax:

    .. code-block:: markdown

       :abbr[HTML]{title="HyperText Markup Language"}
    """

    def __init__(self) -> None:
        super().__init__('text_directive', r':(?=[A-Za-z])', ':')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        parsed = parse_text_directive_head(text, match.start() + 1, state)
        if parsed is None:
            return None, match.start()

        name, label, attributes, end = parsed
        children = parser.parse_inlines(label, state) if label is not None else []
        return TextDirectiveNode(name=name, attributes=attributes, children=children), end


class Role(InlineRule):
    """Parse MyST-style inline roles.

    Markdown syntax:

    .. code-block:: markdown

       {iconify}`devicon:pypi`
    """

    def __init__(self) -> None:
        super().__init__('role', r'\{(?=[A-Za-z])', '{')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        parsed = parse_role(text, match.start())
        if parsed is None:
            return None, match.start()

        name, label, end = parsed
        return TextDirectiveNode(name=name, children=parser.parse_inlines(label, state)), end


def parse_role(text: str, start: int = 0) -> tuple[str, str, int] | None:
    if start >= len(text) or text[start] != '{':
        return None

    name_end = text.find('}', start + 1)
    if name_end == -1:
        return None
    name = text[start + 1 : name_end]
    if NAME_RE.fullmatch(name) is None:
        return None

    tick_start = name_end + 1
    if tick_start >= len(text) or text[tick_start] != '`':
        return None

    tick_end = tick_start
    while tick_end < len(text) and text[tick_end] == '`':
        tick_end += 1
    fence = text[tick_start:tick_end]
    closing = text.find(fence, tick_end)
    if closing == -1:
        return None

    return name, text[tick_end:closing], closing + len(fence)


def parse_text_directive_head(
    text: str, start: int, state: BlockState | None
) -> tuple[str, str | None, dict[str, str] | None, int] | None:
    if state is None:
        return parse_directive_head(text, start)

    match = NAME_RE.match(text, start)
    if match is None:
        return None

    name = match.group(0)
    index = match.end()
    label: str | None = None
    attributes: dict[str, str] | None = None
    square_pairs, brace_pairs = directive_bracket_pairs(text, state)

    if index < len(text) and text[index] == '[':
        end = square_pairs.get(index)
        if end is None:
            return None
        label = text[index + 1 : end]
        index = end + 1

    if index < len(text) and text[index] == '{':
        end = brace_pairs.get(index)
        if end is None:
            return None
        attributes = parse_attributes(text[index + 1 : end])
        index = end + 1

    return name, label, attributes, index


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
