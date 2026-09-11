from __future__ import annotations

from bisect import bisect_left
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Literal as LiteralNode
from wenmode.nodes import Node, Parent
from wenmode.utils import is_escaped

from .._parser.inlines import parse_text_children
from .._parser.rule_base import InlineCandidate, InlineRule
from .._parser.state import BlockState
from .._parser.store import StateKey

if TYPE_CHECKING:
    from wenmode.parser import Parser

ClosingDelimiterCache = dict[tuple[int, int], tuple[str, object, list[int]]]
InlineParse = Callable[['Parser', str, int, BlockState], tuple[Node | None, int]]
DECLARATIVE_INLINE_DEPTH = StateKey[int]('wenmode.declarative.inline_depth', lambda: 0)
DECLARATIVE_CLOSING_DELIMITERS = StateKey[ClosingDelimiterCache]('wenmode.declarative.closing_delimiters', lambda: {})


class DelimitedRule(InlineRule):
    """Shared delimiter dispatch and validation for declarative inline rules."""

    opening_delimiter: str
    closer: str

    def __init__(
        self,
        *,
        name: str,
        opener: str,
        closer: str,
        allow_newline: bool,
        reject_empty: bool,
        reject_opening_whitespace: bool,
        reject_closing_whitespace: bool,
        reject_longer_run: bool,
        strip_content: bool,
        escape: bool,
    ) -> None:
        if not opener:
            raise ValueError('opener must not be empty')
        if not closer:
            raise ValueError('closer must not be empty')
        self.opening_delimiter = opener
        self.closer = closer
        self.allow_newline = allow_newline
        self.reject_empty = reject_empty
        self.reject_opening_whitespace = reject_opening_whitespace
        self.reject_closing_whitespace = reject_closing_whitespace
        self.reject_longer_run = reject_longer_run
        self.strip_content = strip_content
        self.escape = escape
        super().__init__(name=name, opener=opener[0])
        if len(opener) > 1:
            self.openers = ()

    def search_candidate(self, text: str, pos: int = 0) -> InlineCandidate | None:
        start = text.find(self.opening_delimiter, pos)
        if start == -1:
            return None
        return InlineCandidate(start)

    def _opening_content_start(self, text: str, start: int) -> int | None:
        if not text.startswith(self.opening_delimiter, start):
            return None
        if self.escape and is_escaped(text, start):
            return None
        if self.reject_longer_run and _is_delimiter_run_extended(text, start, self.opening_delimiter):
            return None

        content_start = start + len(self.opening_delimiter)
        if content_start >= len(text):
            return None
        if self.reject_opening_whitespace and text[content_start].isspace():
            return None
        return content_start

    def _is_closing_delimiter(self, text: str, start: int) -> bool:
        return (
            start > 0
            and (not self.escape or not is_escaped(text, start))
            and (not self.reject_longer_run or not _is_delimiter_run_extended(text, start, self.closer))
            and (not self.reject_closing_whitespace or not text[start - 1].isspace())
        )


class InlineDelimited(DelimitedRule):
    """Configurable inline rule for paired literal delimiters."""

    def __init__(
        self,
        *,
        name: str,
        node: type[Parent],
        opener: str,
        closer: str,
        allow_newline: bool = True,
        reject_empty: bool = True,
        reject_opening_whitespace: bool = True,
        reject_closing_whitespace: bool = True,
        reject_longer_run: bool = True,
        strip_content: bool = False,
        escape: bool = True,
    ) -> None:
        self.node = node
        super().__init__(
            name=name,
            opener=opener,
            closer=closer,
            allow_newline=allow_newline,
            reject_empty=reject_empty,
            reject_opening_whitespace=reject_opening_whitespace,
            reject_closing_whitespace=reject_closing_whitespace,
            reject_longer_run=reject_longer_run,
            strip_content=strip_content,
            escape=escape,
        )
        self._node_factory = _parent_node_factory(self)
        self._parse_impl: InlineParse
        if (
            opener == closer
            and not strip_content
            and allow_newline
            and reject_empty
            and reject_opening_whitespace
            and reject_closing_whitespace
            and reject_longer_run
            and escape
        ):
            self._parse_impl = self._parse_simple
        elif (
            strip_content
            and not allow_newline
            and reject_empty
            and not reject_opening_whitespace
            and not reject_closing_whitespace
            and not reject_longer_run
            and escape
        ):
            self._parse_impl = self._parse_trimmed
        else:
            self._parse_impl = self._parse_general

    def parse(
        self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
    ) -> tuple[Node | None, int]:
        start = candidate.start
        return self._parse_impl(parser, text, start, state)

    def _parse_general(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        value_start = self._opening_content_start(text, start)
        if value_start is None:
            return None, start

        content = find_content_range(text, value_start, self, state)
        if content is None:
            return None, start

        close, value_start, value_end = content
        return self.create_node(parser, text, state, value_start, value_end), close + len(self.closer)

    def _parse_simple(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        value_start = self._opening_content_start(text, start)
        if value_start is None:
            return None, start

        close = find_closing_delimiter(text, value_start, self, state)
        if close == -1 or close == value_start:
            return None, start

        return self.create_node(parser, text, state, value_start, close), close + len(self.closer)

    def _parse_trimmed(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        content_start = self._opening_content_start(text, start)
        if content_start is None:
            return None, start

        close = text.find(self.closer, content_start)
        while close != -1:
            if not self._is_closing_delimiter(text, close):
                close = text.find(self.closer, close + 1)
                continue

            stripped = stripped_content_range(text, content_start, close)
            if stripped is None:
                close = text.find(self.closer, close + len(self.closer))
                continue

            value_start, value_end = stripped
            if has_newline(text, value_start, value_end):
                return None, start

            node = self.create_node(parser, text, state, value_start, value_end)
            return node, close + len(self.closer)
        return None, start

    def create_node(self, parser: Parser, text: str, state: BlockState, value_start: int, value_end: int) -> Node:
        value = text[value_start:value_end]
        children = parse_text_children(
            parser, DECLARATIVE_INLINE_DEPTH, value, state, parser.inline_source(text, state, value_start, value_end)
        )
        return self._node_factory(children=children)


class InlineLiteral(DelimitedRule):
    """Configurable delimiter rule that produces literal nodes."""

    def __init__(
        self,
        *,
        name: str,
        node: type[LiteralNode],
        opener: str,
        closer: str,
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
        self.node = node
        self.reject_closing_before_digit = reject_closing_before_digit
        self.reject_adjacent_delimiter = reject_adjacent_delimiter
        super().__init__(
            name=name,
            opener=opener,
            closer=closer,
            allow_newline=allow_newline,
            reject_empty=reject_empty,
            reject_opening_whitespace=reject_opening_whitespace,
            reject_closing_whitespace=reject_closing_whitespace,
            reject_longer_run=reject_longer_run,
            strip_content=strip_content,
            escape=escape,
        )
        self._node_factory = _literal_node_factory(self)

    def parse(
        self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
    ) -> tuple[Node | None, int]:
        start = candidate.start
        if self.reject_adjacent_delimiter and _is_delimiter_run_extended(text, start, self.opening_delimiter):
            return None, start
        value_start = self._opening_content_start(text, start)
        if value_start is None:
            return None, start

        content = find_content_range(text, value_start, self, state)
        if content is None:
            return None, start

        close, value_start, value_end = content
        return self._node_factory(value=text[value_start:value_end]), close + len(self.closer)

    def _is_closing_delimiter(self, text: str, start: int) -> bool:
        return (
            super()._is_closing_delimiter(text, start)
            and (not self.reject_adjacent_delimiter or not _is_adjacent_closing_delimiter(text, start, self.closer))
            and (
                not self.reject_closing_before_digit
                or start + len(self.closer) >= len(text)
                or not text[start + len(self.closer)].isdigit()
            )
        )


def _parent_node_factory(syntax: InlineDelimited) -> Callable[..., Node]:
    if not issubclass(syntax.node, Parent):
        raise TypeError(f'{syntax.name!r} requires a Parent node for children content')
    return cast(Callable[..., Node], syntax.node)


def _literal_node_factory(syntax: InlineLiteral) -> Callable[..., Node]:
    if not issubclass(syntax.node, LiteralNode):
        raise TypeError(f'{syntax.name!r} requires a Literal node for value content')
    return cast(Callable[..., Node], syntax.node)


def find_content_range(text: str, start: int, syntax: DelimitedRule, state: BlockState) -> tuple[int, int, int] | None:
    close = find_closing_delimiter(text, start, syntax, state)
    while close != -1:
        value_start, value_end = start, close
        if syntax.strip_content:
            stripped = stripped_content_range(text, value_start, value_end)
            if stripped is None:
                close = find_closing_delimiter(text, close + len(syntax.closer), syntax, state)
                continue
            value_start, value_end = stripped

        if syntax.reject_empty and value_end == value_start:
            return None
        if not syntax.allow_newline and has_newline(text, value_start, value_end):
            return None
        return close, value_start, value_end
    return None


def find_closing_delimiter(text: str, start: int, syntax: DelimitedRule, state: BlockState) -> int:
    positions = closing_delimiter_positions(
        text, state, syntax, lambda index: syntax._is_closing_delimiter(text, index)
    )
    return next_closing_delimiter(positions, start)


def closing_delimiter_positions(
    text: str, state: BlockState, syntax: DelimitedRule, is_closer: Callable[[int], bool]
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


def _is_adjacent_closing_delimiter(text: str, start: int, delimiter: str) -> bool:
    return (start > 0 and text[start - 1] == delimiter[0] and not is_escaped(text, start - 1)) or (
        start + len(delimiter) < len(text) and text[start + len(delimiter)] == delimiter[-1]
    )


def _is_delimiter_run_extended(text: str, start: int, delimiter: str) -> bool:
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
