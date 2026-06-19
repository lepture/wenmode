from __future__ import annotations

import bisect
from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, cast

from wenmode._positions import advance_point
from wenmode.nodes import Node, Point, Position

LineSource = str | Iterable[str]
T = TypeVar('T')


@dataclass(frozen=True, slots=True)
class SourceSegment:
    """Map a contiguous slice of generated parser text to source coordinates."""

    start: int
    end: int
    point: Point


class SourceMap:
    """Map parser text offsets back to source points."""

    __slots__ = ('_cached_offset', '_cached_point', '_segment_starts', '_text_length', 'segments', 'text')

    def __init__(self, text: str, segments: list[SourceSegment]) -> None:
        self.text = text
        self._text_length = len(text)
        self.segments = segments
        self._segment_starts = [segment.start for segment in segments]
        self._cached_offset: int | None = None
        self._cached_point: Point | None = None

    @classmethod
    def contiguous(cls, text: str, point: Point) -> SourceMap:
        return cls(text, [SourceSegment(0, len(text), point)])

    @classmethod
    def from_parts(cls, parts: list[tuple[str, Point]]) -> SourceMap:
        text_parts: list[str] = []
        segments: list[SourceSegment] = []
        offset = 0
        for text, point in parts:
            text_parts.append(text)
            segments.append(SourceSegment(offset, offset + len(text), point))
            offset += len(text)
        return cls(''.join(text_parts), segments)

    def point(self, offset: int) -> Point:
        if not self.segments:
            return Point(line=1, column=1, offset=0)

        if offset < 0:
            offset = 0
        elif offset > self._text_length:
            offset = self._text_length
        if offset == self._cached_offset and self._cached_point is not None:
            return self._cached_point

        if len(self.segments) == 1:
            segment = self.segments[0]
        else:
            segment = self._segment_at(offset)
        if offset == segment.start:
            point = segment.point
        elif segment.start < offset <= segment.end:
            point = advance_point(segment.point, self.text[segment.start : offset])
        elif offset <= self.segments[0].start:
            point = self.segments[0].point
        else:
            segment = self.segments[-1]
            point = advance_point(segment.point, self.text[segment.start : segment.end])

        self._cached_offset = offset
        self._cached_point = point
        return point

    def _segment_at(self, offset: int) -> SourceSegment:
        index = bisect.bisect_left(self._segment_starts, offset)
        if index < len(self.segments) and self._segment_starts[index] == offset:
            return self.segments[index]
        if index == 0:
            return self.segments[0]
        return self.segments[index - 1]

    def position(self, start: int, end: int) -> Position:
        return Position(start=self.point(start), end=self.point(end))

    def slice(self, start: int, end: int) -> SourceMap:
        if start < 0:
            start = 0
        elif start > self._text_length:
            start = self._text_length
        if end < start:
            end = start
        elif end > self._text_length:
            end = self._text_length
        if start == 0 and end == self._text_length:
            return self

        text = self.text[start:end]
        segments: list[SourceSegment] = []
        for segment in self.segments:
            if segment.end < start or segment.start > end:
                continue
            segment_start = max(segment.start, start)
            segment_end = min(segment.end, end)
            if segment_start > segment_end:
                continue
            if segment_start == segment.start:
                point = segment.point
            else:
                point = self.point(segment_start)
            segments.append(
                SourceSegment(
                    start=segment_start - start,
                    end=segment_end - start,
                    point=point,
                )
            )
        if not segments:
            segments.append(SourceSegment(0, 0, self.point(start)))
        return SourceMap(text, segments)

    def line_points(self, lines: list[str]) -> list[Point]:
        points: list[Point] = []
        offset = 0
        for line in lines:
            points.append(self.point(offset))
            offset += len(line)
        return points


class SourceCollector:
    """Collect source spans for generated nested parser text."""

    __slots__ = ()

    def add(self, index: int, offset: int, text: str) -> None:
        """Add text that originated at ``index`` and ``offset``."""
        return None

    def map(self) -> SourceMap | None:
        """Return the collected source map, if source tracking is enabled."""
        return None


class NullSourceCollector(SourceCollector):
    """No-op source collector used when positions are disabled."""


NULL_SOURCE_COLLECTOR = NullSourceCollector()


class PositionSourceCollector(SourceCollector):
    """Source collector backed by a position-aware tracker."""

    __slots__ = ('parts', 'tracker')

    def __init__(self, tracker: PositionSourceTracker) -> None:
        self.tracker = tracker
        self.parts: list[tuple[str, Point]] = []

    def add(self, index: int, offset: int, text: str) -> None:
        point = self.tracker.point_at_line_offset(index, offset)
        if point is not None:
            self.parts.append((text, point))

    def map(self) -> SourceMap | None:
        if not self.parts:
            return None
        return SourceMap.from_parts(self.parts)


class NullSourceTracker:
    """Source tracker used when positions are disabled."""

    __slots__ = ()

    def bind(self, state: BlockState) -> None:
        """Bind this tracker to a block state."""
        return None

    def point_at_index(self, index: int) -> Point | None:
        return None

    def point_at_line_offset(self, index: int, offset: int) -> Point | None:
        return None

    def position_between(self, start_index: int, end_index: int) -> Position | None:
        return None

    def line_position(self, index: int, start: int, end: int) -> Position | None:
        return None

    def line_text(self, index: int, offset: int, text: str) -> SourceMap | None:
        return None

    def paragraph(self, lines: list[str], start_index: int) -> SourceMap | None:
        return None

    def collect(self) -> SourceCollector:
        return NULL_SOURCE_COLLECTOR


class PositionSourceTracker(NullSourceTracker):
    """Source tracker that maps generated parser text to source positions."""

    __slots__ = ('_state', 'line_points')

    def __init__(self, line_points: list[Point]) -> None:
        self.line_points = line_points
        self._state: BlockState | None = None

    def bind(self, state: BlockState) -> None:
        self._state = state

    def _require_state(self) -> BlockState:
        if self._state is None:  # pragma: no cover
            raise RuntimeError('source tracker is not bound to a state')
        return self._state

    def point_at_index(self, index: int) -> Point | None:
        state = self._require_state()
        if 0 <= index < len(self.line_points):
            return self.line_points[index]
        if index <= 0:
            return Point(line=1, column=1, offset=0)
        if not state.lines or not self.line_points:
            return Point(line=1, column=1, offset=0)
        last_index = len(state.lines) - 1
        return advance_point(self.line_points[last_index], state.lines[last_index])

    def point_at_line_offset(self, index: int, offset: int) -> Point | None:
        point = self.point_at_index(index)
        if point is None:
            return None
        if offset <= 0:
            return point
        return advance_point(point, self._require_state().line_at(index)[:offset])

    def position_between(self, start_index: int, end_index: int) -> Position | None:
        start = self.point_at_index(start_index)
        end = self.point_at_index(end_index)
        if start is None or end is None:
            return None
        return Position(start=start, end=end)

    def line_position(self, index: int, start: int, end: int) -> Position | None:
        start_point = self.point_at_line_offset(index, start)
        end_point = self.point_at_line_offset(index, end)
        if start_point is None or end_point is None:
            return None
        return Position(start=start_point, end=end_point)

    def line_text(self, index: int, offset: int, text: str) -> SourceMap | None:
        point = self.point_at_line_offset(index, offset)
        if point is None:
            return None
        return SourceMap.contiguous(text, point)

    def paragraph(self, lines: list[str], start_index: int) -> SourceMap | None:
        state = self._require_state()
        collector = self.collect()
        for offset, text in enumerate(lines):
            index = start_index + offset
            if index < 0 or index >= len(state.lines):
                return None
            raw_line = state.line_at(index)
            collector.add(index, len(raw_line) - len(text), text)

        source = collector.map()
        if source is None:
            return None
        raw_text = ''.join(lines)
        start = len(raw_text) - len(raw_text.lstrip())
        end = len(raw_text.rstrip())
        return source.slice(start, end)

    def collect(self) -> SourceCollector:
        return PositionSourceCollector(self)


@dataclass(frozen=True)
class StateKey(Generic[T]):
    """Typed key for per-parse extension state.

    Rules and transforms should use ``StateKey`` instead of storing mutable
    per-document data on rule instances.

    :param name: Unique key name. Use a package-qualified name to avoid
        collisions.
    :param factory: Callable that creates the initial value for each parse.
    """

    name: str
    factory: Callable[[], T]


class StateStore:
    """Per-parse storage for extension state."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def get(self, key: StateKey[T]) -> T:
        """Return the value for a key, creating it if necessary.

        :param key: State key to read.
        :returns: Stored value for this parse.
        """
        if key.name not in self._values:
            self._values[key.name] = key.factory()
        return cast(T, self._values[key.name])


class StreamLineBuffer:
    """Lazy line buffer for iterable Markdown sources."""

    def __init__(self, source: Iterable[str], track_positions: bool = False) -> None:
        self.lines: list[str] = []
        if track_positions:
            self.line_points: list[Point] | None = []
        else:
            self.line_points = None
        self._iterator: Iterator[str] = iter(source)
        self._exhausted = False
        self._next_point = Point(line=1, column=1, offset=0)

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
            if self.line_points is not None:
                self.line_points.append(self._next_point)
                self._next_point = advance_point(self._next_point, line)


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
    """

    lines: list[str]
    index: int = 0
    source: NullSourceTracker = field(default_factory=NullSourceTracker)
    store: StateStore = field(default_factory=StateStore)
    depth: int = 0
    pending_inlines: list[tuple[list[Node], str, SourceMap | None]] = field(default_factory=list)
    pending_inline_callbacks: list[Callable[[], None]] = field(default_factory=list)
    defer_inlines: bool = False

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

    def first_nonblank_from_current(self) -> str | None:
        """Return the next nonblank line at or after the current index."""
        index = self.index
        while index < len(self.lines):
            line = self.lines[index]
            if line.strip() != '':
                return line
            index += 1
        return None


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
        super().__init__(
            line_buffer.lines,
            index=index,
            source=source,
            store=store,
            depth=depth,
            pending_inlines=pending_inlines,
            pending_inline_callbacks=pending_inline_callbacks,
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
