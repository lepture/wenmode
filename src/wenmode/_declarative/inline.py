from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Literal as LiteralNode
from wenmode.nodes import Node, Parent
from wenmode.nodes import Text as TextNode
from wenmode.rules.base import InlineRule
from wenmode.state import BlockState, SourceMap, StateKey
from wenmode.utils import is_escaped

from .spec import InlineDelimited, InlineLiteral

if TYPE_CHECKING:
    from wenmode.parser import Parser

DECLARATIVE_INLINE_DEPTH = StateKey[int]('wenmode.declarative.inline_depth', lambda: 0)


def _inline_rule_from_syntax(syntax: InlineDelimited | InlineLiteral) -> InlineRule:
    if isinstance(syntax, InlineLiteral):
        return _InlineLiteralRule(syntax)
    if _is_simple_delimited_children(syntax):
        return _SimpleDelimitedChildrenRule(syntax)
    if _is_trimmed_delimited_children(syntax):
        return _TrimmedDelimitedChildrenRule(syntax)
    return DeclarativeInlineRule(syntax)


def _is_simple_delimited_children(syntax: InlineDelimited) -> bool:
    return (
        syntax.content == 'children'
        and syntax.opener == syntax.closer
        and not syntax.strip_content
        and syntax.allow_newline
        and syntax.reject_empty
        and syntax.reject_opening_whitespace
        and syntax.reject_closing_whitespace
        and syntax.reject_longer_run
        and syntax.escape
    )


def _is_trimmed_delimited_children(syntax: InlineDelimited) -> bool:
    return (
        syntax.content == 'children'
        and syntax.strip_content
        and not syntax.allow_newline
        and syntax.reject_empty
        and not syntax.reject_opening_whitespace
        and not syntax.reject_closing_whitespace
        and not syntax.reject_longer_run
        and syntax.escape
    )


class DeclarativeInlineRule(InlineRule):
    """Runtime inline rule generated from an ``InlineDelimited`` spec."""

    def __init__(self, syntax: InlineDelimited) -> None:
        self.syntax = syntax
        super().__init__(
            name=syntax.name,
            pattern=re.escape(syntax.opener),
            trigger_chars=syntax.trigger_chars or syntax.opener[0],
        )

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        syntax = self.syntax
        start = match.start()
        if syntax.escape and is_escaped(text, start):
            return None, start
        if syntax.reject_longer_run and is_part_of_longer_delimiter_run(text, start, syntax.opener):
            return None, start

        value_start = match.end()
        if value_start >= len(text):
            return None, start
        if syntax.reject_opening_whitespace and text[value_start].isspace():
            return None, start

        content = find_delimited_content_range(text, value_start, syntax)
        if content is None:
            return None, start

        close, value_start, value_end = content
        node = create_delimited_node(parser, state, text, value_start, value_end, syntax)
        return node, close + len(syntax.closer)


class _SimpleDelimitedChildrenRule(InlineRule):
    """Fast path for parent nodes with matching literal delimiters."""

    def __init__(self, syntax: InlineDelimited) -> None:
        self.syntax = syntax
        self._node_factory = _parent_node_factory(syntax)
        super().__init__(
            name=syntax.name,
            pattern=re.escape(syntax.opener),
            trigger_chars=syntax.trigger_chars or syntax.opener[0],
        )

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        syntax = self.syntax
        start = match.start()
        if is_escaped(text, start) or is_part_of_longer_delimiter_run(text, start, syntax.opener):
            return None, start

        value_start = match.end()
        if value_start >= len(text) or text[value_start].isspace():
            return None, start

        close = find_closing_delimiter(text, value_start, syntax)
        if close == -1 or close == value_start:
            return None, start

        value = text[value_start:close]
        children = parse_delimited_children(
            parser,
            value,
            state,
            parser.inline_source(text, state, value_start, close),
        )
        return self._node_factory(children=children), close + len(syntax.closer)


class _TrimmedDelimitedChildrenRule(InlineRule):
    """Fast path for parent nodes whose delimited content is whitespace-trimmed."""

    def __init__(self, syntax: InlineDelimited) -> None:
        self.syntax = syntax
        self._node_factory = _parent_node_factory(syntax)
        super().__init__(
            name=syntax.name,
            pattern=re.escape(syntax.opener),
            trigger_chars=syntax.trigger_chars or syntax.opener[0],
        )

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        syntax = self.syntax
        start = match.start()
        if is_escaped(text, start):
            return None, start

        content_start = match.end()
        if content_start >= len(text):
            return None, start

        close = text.find(syntax.closer, content_start)
        while close != -1:
            if is_escaped(text, close):
                close = text.find(syntax.closer, close + 1)
                continue

            stripped = stripped_content_range(text, content_start, close)
            if stripped is None:
                close = text.find(syntax.closer, close + len(syntax.closer))
                continue

            value_start, value_end = stripped
            value = text[value_start:value_end]
            if has_newline(text, value_start, value_end):
                return None, start

            children = parse_delimited_children(
                parser,
                value,
                state,
                parser.inline_source(text, state, value_start, value_end),
            )
            return self._node_factory(children=children), close + len(syntax.closer)
        return None, start


class _InlineLiteralRule(InlineRule):
    """Runtime inline rule generated from an ``InlineLiteral`` spec."""

    def __init__(self, syntax: InlineLiteral) -> None:
        self.syntax = syntax
        self._node_factory = _literal_node_factory(syntax)
        super().__init__(
            name=syntax.name,
            pattern=re.escape(syntax.opener),
            trigger_chars=syntax.trigger_chars or syntax.opener[0],
        )

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        syntax = self.syntax
        start = match.start()
        if syntax.escape and is_escaped(text, start):
            return None, start
        if syntax.reject_adjacent_delimiter and is_adjacent_to_delimiter(text, start, syntax.opener):
            return None, start
        if syntax.reject_longer_run and is_part_of_longer_delimiter_run(text, start, syntax.opener):
            return None, start

        value_start = match.end()
        if value_start >= len(text):
            return None, start
        if syntax.reject_opening_whitespace and text[value_start].isspace():
            return None, start

        content = find_literal_content_range(text, value_start, syntax)
        if content is None:
            return None, start

        close, value_start, value_end = content
        return self._node_factory(value=text[value_start:value_end]), close + len(syntax.closer)


def _parent_node_factory(syntax: InlineDelimited) -> Callable[..., Node]:
    if not issubclass(syntax.node, Parent):
        raise TypeError(f'{syntax.name!r} requires a Parent node for children content')
    return cast(Callable[..., Node], syntax.node)


def _literal_node_factory(syntax: InlineDelimited | InlineLiteral) -> Callable[..., Node]:
    if not issubclass(syntax.node, LiteralNode):
        raise TypeError(f'{syntax.name!r} requires a Literal node for value content')
    return cast(Callable[..., Node], syntax.node)


def create_delimited_node(
    parser: Parser,
    state: BlockState,
    text: str,
    value_start: int,
    value_end: int,
    syntax: InlineDelimited,
) -> Node:
    node_class = syntax.node
    value = text[value_start:value_end]
    if syntax.content == 'children':
        if not issubclass(node_class, Parent):
            raise TypeError(f'{syntax.name!r} requires a Parent node for children content')
        children = parse_delimited_children(
            parser,
            value,
            state,
            parser.inline_source(text, state, value_start, value_end),
        )
        node_factory = cast(Callable[..., Node], node_class)
        return node_factory(children=children)

    if syntax.content == 'value':
        return _literal_node_factory(syntax)(value=value)

    raise TypeError(f'{syntax.name!r} uses unsupported content mode {syntax.content!r}')


def parse_delimited_children(
    parser: Parser,
    value: str,
    state: BlockState,
    source: SourceMap | None,
) -> list[Node]:
    depth = state.store.get(DECLARATIVE_INLINE_DEPTH)
    if depth >= parser.max_container_depth:
        return [TextNode(value=value)]

    state.store.set(DECLARATIVE_INLINE_DEPTH, depth + 1)
    try:
        return parser.parse_inlines(value, state, source=source)
    finally:
        state.store.set(DECLARATIVE_INLINE_DEPTH, depth)


def find_delimited_content_range(text: str, start: int, syntax: InlineDelimited) -> tuple[int, int, int] | None:
    close = find_closing_delimiter(text, start, syntax)
    while close != -1:
        value_start, value_end = start, close
        if syntax.strip_content:
            stripped = stripped_content_range(text, value_start, value_end)
            if stripped is None:
                close = find_closing_delimiter(text, close + len(syntax.closer), syntax)
                continue
            value_start, value_end = stripped

        if syntax.reject_empty and value_end == value_start:
            return None
        if not syntax.allow_newline and has_newline(text, value_start, value_end):
            return None
        return close, value_start, value_end
    return None


def find_literal_content_range(text: str, start: int, syntax: InlineLiteral) -> tuple[int, int, int] | None:
    close = find_literal_closing_delimiter(text, start, syntax)
    while close != -1:
        value_start, value_end = start, close
        if syntax.strip_content:
            stripped = stripped_content_range(text, value_start, value_end)
            if stripped is None:
                close = find_literal_closing_delimiter(text, close + len(syntax.closer), syntax)
                continue
            value_start, value_end = stripped

        if syntax.reject_empty and value_end == value_start:
            return None
        if not syntax.allow_newline and has_newline(text, value_start, value_end):
            return None
        return close, value_start, value_end
    return None


def find_closing_delimiter(text: str, start: int, syntax: InlineDelimited) -> int:
    index = text.find(syntax.closer, start)
    while index != -1:
        if is_closing_delimiter(text, index, syntax):
            return index
        index = text.find(syntax.closer, index + 1)
    return -1


def find_literal_closing_delimiter(text: str, start: int, syntax: InlineLiteral) -> int:
    index = text.find(syntax.closer, start)
    while index != -1:
        if is_literal_closing_delimiter(text, index, syntax):
            return index
        index = text.find(syntax.closer, index + 1)
    return -1


def is_closing_delimiter(text: str, start: int, syntax: InlineDelimited) -> bool:
    return (
        (not syntax.escape or not is_escaped(text, start))
        and (not syntax.reject_longer_run or not is_part_of_longer_delimiter_run(text, start, syntax.closer))
        and start > 0
        and (not syntax.reject_closing_whitespace or not text[start - 1].isspace())
        and text[start - 1] != syntax.closer[0]
    )


def is_literal_closing_delimiter(text: str, start: int, syntax: InlineLiteral) -> bool:
    return (
        (not syntax.escape or not is_escaped(text, start))
        and (not syntax.reject_longer_run or not is_part_of_longer_delimiter_run(text, start, syntax.closer))
        and (not syntax.reject_adjacent_delimiter or not is_adjacent_closing_delimiter(text, start, syntax.closer))
        and start > 0
        and (not syntax.reject_closing_whitespace or not text[start - 1].isspace())
        and (
            not syntax.reject_closing_before_digit
            or start + len(syntax.closer) >= len(text)
            or not text[start + len(syntax.closer)].isdigit()
        )
    )


def is_adjacent_to_delimiter(text: str, start: int, delimiter: str) -> bool:
    return (
        (start > 0 and text[start - 1] == delimiter[0])
        or (start + len(delimiter) < len(text) and text[start + len(delimiter)] == delimiter[-1])
    )


def is_adjacent_closing_delimiter(text: str, start: int, delimiter: str) -> bool:
    return (
        (start > 0 and text[start - 1] == delimiter[0] and not is_escaped(text, start - 1))
        or (start + len(delimiter) < len(text) and text[start + len(delimiter)] == delimiter[-1])
    )


def is_part_of_longer_delimiter_run(text: str, start: int, delimiter: str) -> bool:
    return (
        (start > 0 and text[start - 1] == delimiter[0])
        or (start + len(delimiter) < len(text) and text[start + len(delimiter)] == delimiter[-1])
    )


def has_newline(text: str, start: int, end: int) -> bool:
    return '\n' in text[start:end] or '\r' in text[start:end]


def stripped_content_range(text: str, start: int, end: int) -> tuple[int, int] | None:
    original_start = start
    original_end = end
    while start < end and text[start].isspace():
        start += 1
    while end > start and text[end - 1].isspace():
        end -= 1
    if end > start:
        return start, end
    for index in range(original_end - 1, original_start - 1, -1):
        if text[index] != '\n':
            return index, index + 1
    return None
