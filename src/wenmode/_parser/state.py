from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field

from wenmode.nodes import Node

from .source import NullSourceTracker, SourceMap
from .store import StateStore


class StreamLineBuffer:
    """Lazy line buffer for iterable Markdown sources."""

    def __init__(self, source: Iterable[str], track_positions: bool = False) -> None:
        self.lines: list[str] = []
        if track_positions:
            self.line_offsets: list[int] | None = []
        else:
            self.line_offsets = None
        self._iterator: Iterator[str] = iter(source)
        self._exhausted = False
        self._next_offset = 0

    def has(self, index: int) -> bool:
        """Return whether a line index can be read."""
        self._fill(index)
        return index < len(self.lines)

    def get(self, index: int) -> str:
        """Return a buffered line by absolute index."""
        self._fill(index)
        return self.lines[index]

    def _fill(self, index: int) -> None:
        while not self._exhausted and index >= len(self.lines):
            try:
                line = next(self._iterator)
            except StopIteration:
                self._exhausted = True
                break
            self.lines.append(line)
            if self.line_offsets is not None:
                self.line_offsets.append(self._next_offset)
                self._next_offset += len(line)


@dataclass
class BlockState:
    """Mutable state for one block parse.

    Custom block and continuation rules receive this object and should advance
    it when they consume input.

    :param lines: Source lines for this block parse.
    :param index: Current line index.
    :param store: Per-parse extension state store.
    :param depth: Container nesting depth.
    :param pending_inlines: Deferred inline parse targets.
    :param pending_inline_callbacks: Callbacks to run after deferred inline
        parsing is resolved.
    :param defer_inlines: Whether inline parsing is currently deferred.
    :param inline_sources: Active inline source stack for nested inline parsing.
    """

    lines: list[str]
    index: int = 0
    source: NullSourceTracker = field(default_factory=NullSourceTracker)
    store: StateStore = field(default_factory=StateStore)
    depth: int = 0
    pending_inlines: list[tuple[list[Node], str, SourceMap | None]] = field(default_factory=list)
    pending_inline_callbacks: list[Callable[[], None]] = field(default_factory=list)
    defer_inlines: bool = False
    inline_sources: list[SourceMap] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.source.bind(self)

    @property
    def done(self) -> bool:
        """Whether the state has consumed all available lines."""
        return self.index >= len(self.lines)

    @property
    def line(self) -> str:
        """Current source line."""
        return self.lines[self.index]

    def advance(self, count: int = 1) -> None:
        """Advance the current line index.

        :param count: Number of lines to consume.
        """
        self.index += count

    def has(self, offset: int = 0) -> bool:
        """Return whether a line exists at an offset from the current index."""
        return self.has_index(self.index + offset)

    def peek(self, offset: int = 0) -> str:
        """Return a line at an offset from the current index."""
        return self.line_at(self.index + offset)

    def has_index(self, index: int) -> bool:
        """Return whether an absolute line index is available."""
        return self.index <= index < len(self.lines)

    def line_at(self, index: int) -> str:
        """Return a line by absolute index."""
        return self.lines[index]


class StreamBlockState(BlockState):
    """Block state backed by a lazy :class:`StreamLineBuffer`."""

    def __init__(
        self,
        line_buffer: StreamLineBuffer,
        index: int = 0,
        source: NullSourceTracker | None = None,
        store: StateStore | None = None,
        depth: int = 0,
        pending_inlines: list[tuple[list[Node], str, SourceMap | None]] | None = None,
        pending_inline_callbacks: list[Callable[[], None]] | None = None,
        defer_inlines: bool = False,
        inline_sources: list[SourceMap] | None = None,
    ) -> None:
        self.line_buffer = line_buffer
        if source is None:
            source = NullSourceTracker()
        if store is None:
            store = StateStore()
        if pending_inlines is None:
            pending_inlines = []
        if pending_inline_callbacks is None:
            pending_inline_callbacks = []
        if inline_sources is None:
            inline_sources = []
        super().__init__(
            line_buffer.lines,
            index=index,
            source=source,
            store=store,
            depth=depth,
            pending_inlines=pending_inlines,
            pending_inline_callbacks=pending_inline_callbacks,
            defer_inlines=defer_inlines,
            inline_sources=inline_sources,
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
