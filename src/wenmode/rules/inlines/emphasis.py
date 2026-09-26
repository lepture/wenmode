from __future__ import annotations

import re
from bisect import bisect_left
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from wenmode.nodes import Emphasis as EmphasisNode
from wenmode.nodes import Node, Parent, Position
from wenmode.nodes import Strong as StrongNode
from wenmode.nodes import Text as TextNode
from wenmode.utils.cjk import (
    is_cjk_character,
    is_ideographic_variation_selector,
    is_non_cjk_punctuation,
    is_punctuation,
)

from ..._parser.rule_base import InlineCandidate, InlineRule
from ..._parser.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser

_PLACEHOLDER_TEXT = '\ufffc'
_TEXT_PARTS = re.compile(r'\*+|_+|[^*_]+')


class Emphasis(InlineRule):
    """Parse emphasis and strong emphasis delimiters.

    Markdown syntax:

    .. code-block:: markdown

       *emphasis* and **strong**
    """

    name = 'emphasis'
    pattern = r'(?:\*+|_+)'

    def __init__(self, cjk_friendly: bool = False) -> None:
        super().__init__()
        self.cjk_friendly = cjk_friendly

    def parse(
        self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
    ) -> tuple[Node | None, int]:
        return None, candidate.start

    def parse_emphasis_sequence(self, nodes: list[Node], max_depth: int = 20) -> list[Node]:
        return parse_emphasis_sequence(nodes, cjk_friendly=self.cjk_friendly, max_depth=max_depth)


@dataclass(slots=True)
class _Part:
    node: Node
    index: int
    depth: int
    next: _Part | None = field(default=None, kw_only=True)


@dataclass(slots=True)
class _Delimiter(_Part):
    """A linked part with immutable flanking metadata and mutable availability.

    Keep the original text separately: folding can replace this part's node
    with a subtree, but only after retiring it as a matching delimiter.
    """

    text: TextNode
    marker: str
    can_open: bool
    can_close: bool
    original_length: int
    active: bool = True
    depth_barrier: int | None = None

    @property
    def length(self) -> int:
        return len(self.text.value)

    def consume(self, size: int, *, opening: bool) -> None:
        text = self.text
        if text.position is not None:
            start, end = text.position.start, text.position.start + len(text.value)
            text.position = Position(start=start, end=end - size) if opening else Position(start=start + size, end=end)
        text.value = text.value[:-size] if opening else text.value[size:]
        if not text.value:
            self.active = False


@dataclass(slots=True)
class _OpenerGroup:
    remainder: int
    can_close: bool
    positions: list[int] = field(default_factory=list)
    previous: list[int] = field(default_factory=list)

    def append(self, position: int) -> None:
        self.previous.append(len(self.positions) - 1)
        self.positions.append(position)

    def find_before(self, delimiters: list[_Delimiter], position: int) -> int | None:
        index = bisect_left(self.positions, position) - 1
        if index < 0:
            return None
        if delimiters[self.positions[index]].active:
            return self.positions[index]
        exhausted: list[int] = []
        while index >= 0 and not delimiters[self.positions[index]].active:
            exhausted.append(index)
            index = self.previous[index]
        # Exhaustion is permanent. Compress these links so later searches do
        # not repeatedly walk the same removed delimiter range.
        for removed in exhausted:
            self.previous[removed] = index
        return self.positions[index] if index >= 0 else None


class _OpenerIndex:
    """Find eligible openers without scanning intervening closer-only runs."""

    def __init__(self, delimiters: list[_Delimiter]) -> None:
        self.delimiters = delimiters
        groups: dict[tuple[str, int, bool], _OpenerGroup] = {}
        single_runs = all(delimiter.original_length == 1 for delimiter in delimiters)
        for position, delimiter in enumerate(delimiters):
            if delimiter.can_open:
                # Two single-character runs cannot violate the rule of three,
                # so their flanking categories can share one lookup group.
                key = (delimiter.marker, delimiter.original_length % 3, delimiter.can_close and not single_runs)
                group = groups.get(key)
                if group is None:
                    group = groups[key] = _OpenerGroup(key[1], key[2])
                group.append(position)
        self.groups: dict[str, list[_OpenerGroup]] = {'*': [], '_': []}
        for (marker, _, _), group in groups.items():
            self.groups[marker].append(group)

    def find(self, closer: _Delimiter, position: int, bottom: int) -> int | None:
        opener = None
        remainder = closer.original_length % 3
        for group in self.groups[closer.marker]:
            # Consumption and retirement never change an opener's lookup
            # category or the original lengths used by the rule of three.
            if (group.can_close or closer.can_open) and (group.remainder + remainder) % 3 == 0 and group.remainder != 0:
                continue
            candidate = group.find_before(self.delimiters, position)
            if candidate is not None and candidate >= bottom and (opener is None or candidate > opener):
                opener = candidate
        return opener


@dataclass(slots=True)
class _Span:
    """A proposed match; contained delimiters retire only after acceptance."""

    children: list[Node]
    depth: int = 0
    has_content: bool = False
    barrier: int | None = None
    retired_delimiters: list[_Delimiter] | None = None


class _EmphasisSequence:
    """Scan once, then collapse matches without shifting source-order indices.

    Part and delimiter indices never change. Active parts form a forward chain;
    retired parts may remain in the opener index but never become active again.
    Each part caches its subtree's emphasis depth, updated only when wrapping it.
    """

    def __init__(self, nodes: list[Node], cjk_friendly: bool, max_depth: int) -> None:
        self.head: _Part | None = None
        self.tail: _Part | None = None
        self.part_count = 0
        self.delimiters: list[_Delimiter] = []
        self.max_depth = max_depth
        source = ''.join(node.value if isinstance(node, TextNode) else _PLACEHOLDER_TEXT for node in nodes)
        offset = 0
        for node in nodes:
            if isinstance(node, TextNode):
                if node._parse_emphasis:
                    self._split_text(node, source, offset, cjk_friendly)
                else:
                    self._append(_Part(node, self.part_count, 0))
                offset += len(node.value)
            else:
                depth = _node_emphasis_depth(node) if isinstance(node, Parent) else 0
                self._append(_Part(node, self.part_count, depth))
                offset += len(_PLACEHOLDER_TEXT)

    def _append(self, part: _Part) -> None:
        if self.tail is None:
            self.head = part
        else:
            self.tail.next = part
        self.tail = part
        self.part_count += 1

    def _split_text(self, node: TextNode, source: str, offset: int, cjk_friendly: bool) -> None:
        for match in _TEXT_PARTS.finditer(node.value):
            start, end = match.span()
            value = match.group()
            marker = value[0]
            token = TextNode(value=value, position=_text_position(node, start, end))
            if marker in '*_':
                can_open, can_close = _delimiter_flags(source, offset + start, end - start, marker, cjk_friendly)
                if can_open or can_close:
                    delimiter = _Delimiter(
                        node=token,
                        index=self.part_count,
                        depth=0,
                        text=token,
                        marker=marker,
                        can_open=can_open,
                        can_close=can_close,
                        original_length=end - start,
                    )
                    self.delimiters.append(delimiter)
                    self._append(delimiter)
                    continue
            self._append(_Part(token, self.part_count, 0))

    def process(self) -> list[Node]:
        if self.max_depth <= 0 or len(self.delimiters) < 2:
            return self._result()
        openers = _OpenerIndex(self.delimiters)
        bottoms: dict[tuple[str, int, bool], int] = {}
        position = 0
        while position < len(self.delimiters):
            closer = self.delimiters[position]
            if not closer.active or not closer.can_close:
                position += 1
                continue
            key = (closer.marker, closer.length % 3, closer.can_open)
            opener_position = openers.find(closer, position, bottoms.get(key, 0))
            if opener_position is None:
                bottoms[key] = position
                position += 1
                continue
            opener = self.delimiters[opener_position]
            if opener.depth_barrier is not None and closer.index > opener.depth_barrier:
                position += 1
                continue
            span = self._span(opener, closer)
            if not span.has_content or span.depth >= self.max_depth:
                # Cache only this opener's failed span: other openers and
                # closers revisited before the saturated subtree remain valid.
                opener.depth_barrier = span.barrier
                position += 1
                continue
            self._collapse(opener, closer, span)
            if (opener.active and opener.can_open) or (closer.active and closer.can_close):
                position = max(opener_position, bottoms.get(key, 0))
            else:
                position += 1
        return self._result()

    def _span(self, opener: _Delimiter, closer: _Delimiter) -> _Span:
        children: list[Node] = []
        depth = 0
        has_content = False
        barrier = None
        retired: list[_Delimiter] | None = None
        part = opener.next
        while part is not None and part is not closer:
            children.append(part.node)
            if part.depth > depth:
                depth = part.depth
            has_content = has_content or not isinstance(part.node, TextNode) or bool(part.node.value)
            if part.depth >= self.max_depth:
                barrier = part.index
            if isinstance(part, _Delimiter) and part.active:
                if retired is None:
                    retired = []
                retired.append(part)
            part = part.next
        return _Span(children, depth, has_content, barrier, retired)

    def _collapse(self, opener: _Delimiter, closer: _Delimiter, span: _Span) -> None:
        size = 2 if opener.length >= 2 and closer.length >= 2 else 1
        position = _emphasis_position(opener.text, closer.text, size)
        opener.consume(size, opening=True)
        closer.consume(size, opening=False)
        node = StrongNode(children=span.children) if size == 2 else EmphasisNode(children=span.children)
        node.position = position

        first = opener.next
        assert first is not None
        if span.retired_delimiters is not None:
            for delimiter in span.retired_delimiters:
                delimiter.active = False
        first.node = node
        first.depth = span.depth + 1
        first.next = closer

    def _result(self) -> list[Node]:
        result: list[Node] = []
        part = self.head
        while part is not None:
            if not isinstance(part.node, TextNode) or part.node.value:
                result.append(part.node)
            part = part.next
        return result


def parse_emphasis_sequence(nodes: list[Node], cjk_friendly: bool = False, max_depth: int = 20) -> list[Node]:
    return _EmphasisSequence(nodes, cjk_friendly, max_depth).process()


def _text_position(node: TextNode, start: int, end: int) -> Position | None:
    if node._source_position is not None:
        return node._source_position(start, end)
    if node.position is None:
        return None
    return Position(start=node.position.start + start, end=node.position.start + end)


def _node_emphasis_depth(node: Node) -> int:
    max_depth = 0
    stack = [(node, 0)]
    while stack:
        node, parent_depth = stack.pop()
        depth = parent_depth + 1 if isinstance(node, (EmphasisNode, StrongNode)) else parent_depth
        max_depth = max(max_depth, depth)
        if isinstance(node, Parent):
            stack.extend((child, depth) for child in node.children)
    return max_depth


def _emphasis_position(opener: TextNode, closer: TextNode, size: int) -> Position | None:
    if opener.position is None or closer.position is None:
        return None
    return Position(start=opener.position.end - size, end=closer.position.start + size)


def _delimiter_flags(text: str, start: int, size: int, marker: str, cjk_friendly: bool) -> tuple[bool, bool]:
    previous = text[start - 1] if start > 0 else '\n'
    next_char = text[start + size] if start + size < len(text) else '\n'
    left, right = _cjk_flanking(previous, next_char) if cjk_friendly else _standard_flanking(previous, next_char)
    if marker == '_':
        return left and (not right or is_punctuation(previous)), right and (not left or is_punctuation(next_char))
    return left, right


def _cjk_flanking(previous: str, next_char: str) -> tuple[bool, bool]:
    prev_ws, next_ws = previous.isspace(), next_char.isspace()
    prev_p, next_p = is_non_cjk_punctuation(previous), is_non_cjk_punctuation(next_char)
    prev_cjk = is_cjk_character(previous) or is_ideographic_variation_selector(previous)
    next_cjk = is_cjk_character(next_char)
    left = (not next_ws) and (not next_p or prev_ws or prev_p or prev_cjk)
    right = (not prev_ws) and (not prev_p or next_ws or next_p or next_cjk)
    return left, right


def _standard_flanking(previous: str, next_char: str) -> tuple[bool, bool]:
    prev_ws, next_ws = previous.isspace(), next_char.isspace()
    prev_p, next_p = is_punctuation(previous), is_punctuation(next_char)
    left = (not next_ws) and (not next_p or prev_ws or prev_p)
    right = (not prev_ws) and (not prev_p or next_ws or next_p)
    return left, right
