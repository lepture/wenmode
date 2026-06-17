from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, Callable

from wenmode.nodes import Node

LineSource = str | Iterable[str]


class StreamLineBuffer:
    def __init__(self, source: Iterable[str]) -> None:
        self.lines: list[str] = []
        self._iterator: Iterator[str] = iter(source)
        self._exhausted = False

    def has(self, index: int) -> bool:
        self._fill(index)
        return index < len(self.lines)

    def get(self, index: int) -> str:
        self._fill(index)
        return self.lines[index]

    def _fill(self, index: int) -> None:
        while not self._exhausted and index >= len(self.lines):
            try:
                self.lines.append(next(self._iterator))
            except StopIteration:
                self._exhausted = True
                break


@dataclass
class Reference:
    url: str
    title: str | None = None


@dataclass
class Footnote:
    identifier: str
    label: str
    children: list[Node]


@dataclass
class Abbreviation:
    label: str
    title: str


@dataclass
class BlockState:
    lines: list[str]
    index: int = 0
    references: dict[str, Reference] = field(default_factory=dict)
    footnotes: dict[str, Footnote] = field(default_factory=dict)
    abbreviations: dict[str, Abbreviation] = field(default_factory=dict)
    depth: int = 0
    pending_inlines: list[tuple[list[Node], str]] = field(default_factory=list)
    pending_inline_callbacks: list[Callable[[], None]] = field(default_factory=list)
    inline_cache: dict[str, Any] = field(default_factory=dict)
    defer_inlines: bool = False

    @property
    def done(self) -> bool:
        return self.index >= len(self.lines)

    @property
    def line(self) -> str:
        return self.lines[self.index]

    def advance(self, count: int = 1) -> None:
        self.index += count

    def has(self, offset: int = 0) -> bool:
        return self.has_index(self.index + offset)

    def peek(self, offset: int = 0) -> str:
        return self.line_at(self.index + offset)

    def has_index(self, index: int) -> bool:
        return self.index <= index < len(self.lines)

    def line_at(self, index: int) -> str:
        return self.lines[index]

    def first_nonblank_from_current(self) -> str | None:
        index = self.index
        while index < len(self.lines):
            line = self.lines[index]
            if line.strip() != '':
                return line
            index += 1
        return None

    def get_reference(self, label: str) -> Reference | None:
        return self.references.get(label)

    def get_footnote(self, identifier: str) -> Footnote | None:
        return self.footnotes.get(identifier)

    def get_abbreviation(self, label: str) -> Abbreviation | None:
        return self.abbreviations.get(label)


class StreamBlockState(BlockState):
    def __init__(
        self,
        line_buffer: StreamLineBuffer,
        index: int = 0,
        references: dict[str, Reference] | None = None,
        footnotes: dict[str, Footnote] | None = None,
        abbreviations: dict[str, Abbreviation] | None = None,
        depth: int = 0,
        pending_inlines: list[tuple[list[Node], str]] | None = None,
        pending_inline_callbacks: list[Callable[[], None]] | None = None,
        inline_cache: dict[str, Any] | None = None,
        defer_inlines: bool = False,
    ) -> None:
        self.line_buffer = line_buffer
        super().__init__(
            line_buffer.lines,
            index=index,
            references=references if references is not None else {},
            footnotes=footnotes if footnotes is not None else {},
            abbreviations=abbreviations if abbreviations is not None else {},
            depth=depth,
            pending_inlines=pending_inlines if pending_inlines is not None else [],
            pending_inline_callbacks=pending_inline_callbacks if pending_inline_callbacks is not None else [],
            inline_cache=inline_cache if inline_cache is not None else {},
            defer_inlines=defer_inlines,
        )

    @property
    def done(self) -> bool:
        return not self.has()

    @property
    def line(self) -> str:
        return self.peek()

    def has(self, offset: int = 0) -> bool:
        return self.has_index(self.index + offset)

    def peek(self, offset: int = 0) -> str:
        return self.line_at(self.index + offset)

    def has_index(self, index: int) -> bool:
        return index >= self.index and self.line_buffer.has(index)

    def line_at(self, index: int) -> str:
        return self.line_buffer.get(index)

    def first_nonblank_from_current(self) -> str | None:
        offset = 0
        while self.has(offset):
            line = self.peek(offset)
            if line.strip() != '':
                return line
            offset += 1
        return None
