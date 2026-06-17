from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, cast

from wenmode.nodes import Node

LineSource = str | Iterable[str]
T = TypeVar('T')


@dataclass(frozen=True)
class StateKey(Generic[T]):
    name: str
    factory: Callable[[], T]


class StateStore:
    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def get(self, key: StateKey[T]) -> T:
        if key.name not in self._values:
            self._values[key.name] = key.factory()
        return cast(T, self._values[key.name])


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
class BlockState:
    lines: list[str]
    index: int = 0
    store: StateStore = field(default_factory=StateStore)
    depth: int = 0
    pending_inlines: list[tuple[list[Node], str]] = field(default_factory=list)
    pending_inline_callbacks: list[Callable[[], None]] = field(default_factory=list)
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


class StreamBlockState(BlockState):
    def __init__(
        self,
        line_buffer: StreamLineBuffer,
        index: int = 0,
        store: StateStore | None = None,
        depth: int = 0,
        pending_inlines: list[tuple[list[Node], str]] | None = None,
        pending_inline_callbacks: list[Callable[[], None]] | None = None,
        defer_inlines: bool = False,
    ) -> None:
        self.line_buffer = line_buffer
        super().__init__(
            line_buffer.lines,
            index=index,
            store=store if store is not None else StateStore(),
            depth=depth,
            pending_inlines=pending_inlines if pending_inlines is not None else [],
            pending_inline_callbacks=pending_inline_callbacks if pending_inline_callbacks is not None else [],
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
