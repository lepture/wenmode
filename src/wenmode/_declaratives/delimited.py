from __future__ import annotations

"""Configurable delimited inline rules."""

import re
from bisect import bisect_left
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Literal as LiteralNode
from wenmode.nodes import Node, Parent
from wenmode.nodes import Text as TextNode
from wenmode.rules.base import InlineRule
from wenmode.utils import is_escaped

from .._parser.source import SourceMap
from .._parser.state import BlockState
from .._parser.store import StateKey

if TYPE_CHECKING:
    from wenmode.parser import Parser

ClosingDelimiterCache = dict[tuple[int, int], tuple[str, object, list[int]]]
ClosingDelimiterFinder = Callable[[str, int, 'InlineDelimited | InlineLiteral', BlockState], int]
InlineParse = Callable[['Parser', str, int, BlockState], tuple[Node | None, int]]
DECLARATIVE_INLINE_DEPTH = StateKey[int]('wenmode.declarative.inline_depth', lambda: 0)
DECLARATIVE_CLOSING_DELIMITERS = StateKey[ClosingDelimiterCache]('wenmode.declarative.closing_delimiters', lambda: {})


def _is_simple_delimited_children(syntax: InlineDelimited) -> bool:
    return (
        syntax.opener == syntax.closer
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
        syntax.strip_content
        and not syntax.allow_newline
        and syntax.reject_empty
        and not syntax.reject_opening_whitespace
        and not syntax.reject_closing_whitespace
        and not syntax.reject_longer_run
        and syntax.escape
    )


class InlineDelimited(InlineRule):
    """Configurable inline rule for paired literal delimiters."""

    def __init__(
        self,
        *,
        name: str,
        node: type[Parent],
        opener: str,
        closer: str,
        trigger_chars: str | None = None,
        allow_newline: bool = True,
        reject_empty: bool = True,
        reject_opening_whitespace: bool = True,
        reject_closing_whitespace: bool = True,
        reject_longer_run: bool = True,
        strip_content: bool = False,
        escape: bool = True,
    ) -> None:
        _validate_delimiters(opener, closer)
        self.node = node
        self.opener = opener
        self.closer = closer
        self.allow_newline = allow_newline
        self.reject_empty = reject_empty
        self.reject_opening_whitespace = reject_opening_whitespace
        self.reject_closing_whitespace = reject_closing_whitespace
        self.reject_longer_run = reject_longer_run
        self.strip_content = strip_content
        self.escape = escape
        self._node_factory = _parent_node_factory(self)
        self._parse_impl: InlineParse
        if _is_simple_delimited_children(self):
            self._parse_impl = self._parse_simple
        elif _is_trimmed_delimited_children(self):
            self._parse_impl = self._parse_trimmed
        else:
            self._parse_impl = self._parse_general
        super().__init__(
            name=name, pattern=re.escape(opener), trigger_chars=opener[0] if trigger_chars is None else trigger_chars
        )

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        return self._parse_impl(parser, text, start, state)

    def _parse_general(
        self, parser: Parser, text: str, start: int, state: BlockState
    ) -> tuple[Node | None, int]:
        if not text.startswith(self.opener, start):
            return None, start
        if self.escape and is_escaped(text, start):
            return None, start
        if self.reject_longer_run and is_part_of_longer_delimiter_run(text, start, self.opener):
            return None, start

        value_start = start + len(self.opener)
        if value_start >= len(text):
            return None, start
        if self.reject_opening_whitespace and text[value_start].isspace():
            return None, start

        content = find_content_range(text, value_start, self, state, find_closing_delimiter)
        if content is None:
            return None, start

        close, value_start, value_end = content
        return self._create_node(parser, text, state, value_start, value_end), close + len(self.closer)

    def _parse_simple(
        self, parser: Parser, text: str, start: int, state: BlockState
    ) -> tuple[Node | None, int]:
        if not text.startswith(self.opener, start):
            return None, start
        if is_escaped(text, start) or is_part_of_longer_delimiter_run(text, start, self.opener):
            return None, start

        value_start = start + len(self.opener)
        if value_start >= len(text) or text[value_start].isspace():
            return None, start

        close = find_closing_delimiter(text, value_start, self, state)
        if close == -1 or close == value_start:
            return None, start

        return self._create_node(parser, text, state, value_start, close), close + len(self.closer)

    def _parse_trimmed(
        self, parser: Parser, text: str, start: int, state: BlockState
    ) -> tuple[Node | None, int]:
        if not text.startswith(self.opener, start):
            return None, start
        if is_escaped(text, start):
            return None, start

        content_start = start + len(self.opener)
        if content_start >= len(text):
            return None, start

        close = text.find(self.closer, content_start)
        while close != -1:
            if is_escaped(text, close):
                close = text.find(self.closer, close + 1)
                continue

            stripped = stripped_content_range(text, content_start, close)
            if stripped is None:
                close = text.find(self.closer, close + len(self.closer))
                continue

            value_start, value_end = stripped
            if has_newline(text, value_start, value_end):
                return None, start

            node = self._create_node(parser, text, state, value_start, value_end)
            return node, close + len(self.closer)
        return None, start

    def _create_node(self, parser: Parser, text: str, state: BlockState, value_start: int, value_end: int) -> Node:
        value = text[value_start:value_end]
        children = parse_delimited_children(
            parser, value, state, parser.inline_source(text, state, value_start, value_end)
        )
        return self._node_factory(children=children)


class InlineLiteral(InlineRule):
    """Configurable delimiter rule that produces literal nodes."""

    def __init__(
        self,
        *,
        name: str,
        node: type[LiteralNode],
        opener: str,
        closer: str,
        trigger_chars: str | None = None,
        allow_newline: bool = False,
        reject_empty: bool = True,
        reject_opening_whitespace: bool = True,
        reject_closing_whitespace: bool = True,
        reject_closing_before_digit: bool = False,
        reject_longer_run: bool = False,
        reject_adjacent_delimiter: bool = False,
        strip_content: bool = False,
        escape: bool = True,
    ) -> None:
        _validate_delimiters(opener, closer)
        self.node = node
        self.opener = opener
        self.closer = closer
        self.allow_newline = allow_newline
        self.reject_empty = reject_empty
        self.reject_opening_whitespace = reject_opening_whitespace
        self.reject_closing_whitespace = reject_closing_whitespace
        self.reject_closing_before_digit = reject_closing_before_digit
        self.reject_longer_run = reject_longer_run
        self.reject_adjacent_delimiter = reject_adjacent_delimiter
        self.strip_content = strip_content
        self.escape = escape
        self._node_factory = _literal_node_factory(self)
        super().__init__(
            name=name, pattern=re.escape(opener), trigger_chars=opener[0] if trigger_chars is None else trigger_chars
        )

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        if not text.startswith(self.opener, start):
            return None, start
        if self.escape and is_escaped(text, start):
            return None, start
        if self.reject_adjacent_delimiter and is_adjacent_to_delimiter(text, start, self.opener):
            return None, start
        if self.reject_longer_run and is_part_of_longer_delimiter_run(text, start, self.opener):
            return None, start

        value_start = start + len(self.opener)
        if value_start >= len(text):
            return None, start
        if self.reject_opening_whitespace and text[value_start].isspace():
            return None, start

        content = find_content_range(text, value_start, self, state, find_literal_closing_delimiter)
        if content is None:
            return None, start

        close, value_start, value_end = content
        return self._node_factory(value=text[value_start:value_end]), close + len(self.closer)


def _parent_node_factory(syntax: InlineDelimited) -> Callable[..., Node]:
    if not issubclass(syntax.node, Parent):
        raise TypeError(f'{syntax.name!r} requires a Parent node for children content')
    return cast(Callable[..., Node], syntax.node)


def _literal_node_factory(syntax: InlineLiteral) -> Callable[..., Node]:
    if not issubclass(syntax.node, LiteralNode):
        raise TypeError(f'{syntax.name!r} requires a Literal node for value content')
    return cast(Callable[..., Node], syntax.node)


def _validate_delimiters(opener: str, closer: str) -> None:
    if not opener:
        raise ValueError('opener must not be empty')
    if not closer:
        raise ValueError('closer must not be empty')


def parse_delimited_children(parser: Parser, value: str, state: BlockState, source: SourceMap | None) -> list[Node]:
    depth = state.store.get(DECLARATIVE_INLINE_DEPTH)
    if depth >= parser.max_container_depth:
        return [TextNode(value=value)]

    state.store.set(DECLARATIVE_INLINE_DEPTH, depth + 1)
    try:
        return parser.parse_inlines(value, state, source=source)
    finally:
        state.store.set(DECLARATIVE_INLINE_DEPTH, depth)


def find_content_range(
    text: str,
    start: int,
    syntax: InlineDelimited | InlineLiteral,
    state: BlockState,
    find_closer: ClosingDelimiterFinder,
) -> tuple[int, int, int] | None:
    close = find_closer(text, start, syntax, state)
    while close != -1:
        value_start, value_end = start, close
        if syntax.strip_content:
            stripped = stripped_content_range(text, value_start, value_end)
            if stripped is None:
                close = find_closer(text, close + len(syntax.closer), syntax, state)
                continue
            value_start, value_end = stripped

        if syntax.reject_empty and value_end == value_start:
            return None
        if not syntax.allow_newline and has_newline(text, value_start, value_end):
            return None
        return close, value_start, value_end
    return None


def find_closing_delimiter(text: str, start: int, syntax: InlineDelimited | InlineLiteral, state: BlockState) -> int:
    syntax = cast(InlineDelimited, syntax)
    positions = closing_delimiter_positions(
        text, state, syntax, lambda index: is_closing_delimiter(text, index, syntax)
    )
    return next_closing_delimiter(positions, start)


def find_literal_closing_delimiter(
    text: str, start: int, syntax: InlineDelimited | InlineLiteral, state: BlockState
) -> int:
    syntax = cast(InlineLiteral, syntax)
    positions = closing_delimiter_positions(
        text, state, syntax, lambda index: is_literal_closing_delimiter(text, index, syntax)
    )
    return next_closing_delimiter(positions, start)


def closing_delimiter_positions(
    text: str, state: BlockState, syntax: InlineDelimited | InlineLiteral, is_closer: Callable[[int], bool]
) -> list[int]:
    cache = state.store.get(DECLARATIVE_CLOSING_DELIMITERS)
    key = (id(text), id(syntax))
    cached = cache.get(key)
    if cached is not None and cached[0] is text and cached[1] is syntax:
        return cached[2]

    positions: list[int] = []
    index = text.find(syntax.closer)
    while index != -1:
        if is_closer(index):
            positions.append(index)
        index = text.find(syntax.closer, index + 1)
    cache[key] = (text, syntax, positions)
    return positions


def next_closing_delimiter(positions: list[int], start: int) -> int:
    index = bisect_left(positions, start)
    if index == len(positions):
        return -1
    return positions[index]


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
    return (start > 0 and text[start - 1] == delimiter[0]) or (
        start + len(delimiter) < len(text) and text[start + len(delimiter)] == delimiter[-1]
    )


def is_adjacent_closing_delimiter(text: str, start: int, delimiter: str) -> bool:
    return (start > 0 and text[start - 1] == delimiter[0] and not is_escaped(text, start - 1)) or (
        start + len(delimiter) < len(text) and text[start + len(delimiter)] == delimiter[-1]
    )


def is_part_of_longer_delimiter_run(text: str, start: int, delimiter: str) -> bool:
    return (start > 0 and text[start - 1] == delimiter[0]) or (
        start + len(delimiter) < len(text) and text[start + len(delimiter)] == delimiter[-1]
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
