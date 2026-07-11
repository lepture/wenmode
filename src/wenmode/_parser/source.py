from __future__ import annotations

from bisect import bisect_left
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Position

if TYPE_CHECKING:
    from .state import BlockState, StreamLineBuffer

LineSource = str | Iterable[str]


@dataclass(frozen=True, slots=True)
class SourceSegment:
    """Map a contiguous slice of generated parser text to source offsets."""

    start: int
    end: int
    offset: int


class SourceMap:
    """Map parser text offsets back to source offsets."""

    __slots__ = ('_direct_slice_offsets', '_segment_ends', '_segment_starts', '_text_length', 'segments', 'text')

    def __init__(self, text: str, segments: list[SourceSegment]) -> None:
        self.text = text
        self._text_length = len(text)
        self.segments = segments
        starts = tuple(segment.start for segment in segments)
        ends = tuple(segment.end for segment in segments)
        ordered = all(left <= right for left, right in zip(starts, starts[1:])) and all(
            left <= right for left, right in zip(ends, ends[1:])
        )
        self._direct_slice_offsets = ordered and all(
            left.end <= right.start for left, right in zip(segments, segments[1:])
        )
        if ordered:
            self._segment_starts: tuple[int, ...] | None = starts
            self._segment_ends: tuple[int, ...] | None = ends
        else:
            self._segment_starts = None
            self._segment_ends = None

    @classmethod
    def contiguous(cls, text: str, offset: int) -> SourceMap:
        return cls(text, [SourceSegment(0, len(text), offset)])

    @classmethod
    def from_parts(cls, parts: list[tuple[str, int]]) -> SourceMap:
        text_parts: list[str] = []
        segments: list[SourceSegment] = []
        offset = 0
        for text, source_offset in parts:
            text_parts.append(text)
            segments.append(SourceSegment(offset, offset + len(text), source_offset))
            offset += len(text)
        return cls(''.join(text_parts), segments)

    def source_offset(self, offset: int) -> int:
        if not self.segments:
            return 0

        if offset < 0:
            offset = 0
        elif offset > self._text_length:
            offset = self._text_length

        if offset <= self.segments[0].start:
            return self.segments[0].offset

        if self._segment_starts is None or self._segment_ends is None:
            return self._linear_source_offset(offset)

        index = bisect_left(self._segment_starts, offset)
        if index < len(self.segments) and self._segment_starts[index] == offset:
            return self.segments[index].offset

        index = bisect_left(self._segment_ends, offset)
        if index < len(self.segments):
            segment = self.segments[index]
            if segment.start < offset <= segment.end:
                return segment.offset + offset - segment.start

        segment = self.segments[-1]
        return segment.offset + segment.end - segment.start

    def _linear_source_offset(self, offset: int) -> int:
        for segment in self.segments:
            if offset == segment.start:
                return segment.offset

        for segment in self.segments:
            if segment.start < offset <= segment.end:
                return segment.offset + offset - segment.start

        segment = self.segments[-1]
        return segment.offset + segment.end - segment.start

    def position(self, start: int, end: int) -> Position:
        return Position(start=self.source_offset(start), end=self.source_offset(end))

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
                source_offset = segment.offset
            elif self._direct_slice_offsets and segment_start < segment.end:
                source_offset = segment.offset + segment_start - segment.start
            else:
                source_offset = self.source_offset(segment_start)
            segments.append(
                SourceSegment(
                    start=segment_start - start,
                    end=segment_end - start,
                    offset=source_offset,
                )
            )
        if not segments:
            segments.append(SourceSegment(0, 0, self.source_offset(start)))
        return SourceMap(text, segments)

    def line_offsets(self, lines: list[str]) -> list[int]:
        offsets: list[int] = []
        offset = 0
        for line in lines:
            offsets.append(self.source_offset(offset))
            offset += len(line)
        return offsets


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
        self.parts: list[tuple[str, int]] = []

    def add(self, index: int, offset: int, text: str) -> None:
        source_offset = self.tracker.offset_at_line_offset(index, offset)
        if source_offset is not None:
            self.parts.append((text, source_offset))

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

    def offset_at_index(self, index: int) -> int | None:
        return None

    def offset_at_line_offset(self, index: int, offset: int) -> int | None:
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

    __slots__ = ('_state', 'line_offsets')

    def __init__(self, line_offsets: list[int]) -> None:
        self.line_offsets = line_offsets
        self._state: BlockState | None = None

    def bind(self, state: BlockState) -> None:
        self._state = state

    def _require_state(self) -> BlockState:
        if self._state is None:  # pragma: no cover
            raise RuntimeError('source tracker is not bound to a state')
        return self._state

    def offset_at_index(self, index: int) -> int | None:
        state = self._require_state()
        if 0 <= index < len(self.line_offsets):
            return self.line_offsets[index]
        if index <= 0:
            return 0
        if not state.lines or not self.line_offsets:
            return 0
        last_index = len(state.lines) - 1
        return self.line_offsets[last_index] + len(state.lines[last_index])

    def offset_at_line_offset(self, index: int, offset: int) -> int | None:
        source_offset = self.offset_at_index(index)
        if source_offset is None:
            return None
        if offset <= 0:
            return source_offset
        return source_offset + offset

    def position_between(self, start_index: int, end_index: int) -> Position | None:
        start = self.offset_at_index(start_index)
        end = self.offset_at_index(end_index)
        if start is None or end is None:
            return None
        return Position(start=start, end=end)

    def line_position(self, index: int, start: int, end: int) -> Position | None:
        start_offset = self.offset_at_line_offset(index, start)
        end_offset = self.offset_at_line_offset(index, end)
        if start_offset is None or end_offset is None:
            return None
        return Position(start=start_offset, end=end_offset)

    def line_text(self, index: int, offset: int, text: str) -> SourceMap | None:
        source_offset = self.offset_at_line_offset(index, offset)
        if source_offset is None:
            return None
        return SourceMap.contiguous(text, source_offset)

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


class StreamPositionSourceTracker(PositionSourceTracker):
    """Position tracker backed by a compactable stream line buffer."""

    __slots__ = ('line_buffer',)

    def __init__(self, line_buffer: StreamLineBuffer) -> None:
        super().__init__([])
        self.line_buffer = line_buffer

    def offset_at_index(self, index: int) -> int | None:
        return self.line_buffer.offset_at_index(index)

    def paragraph(self, lines: list[str], start_index: int) -> SourceMap | None:
        collector = self.collect()
        for offset, text in enumerate(lines):
            index = start_index + offset
            raw_line = self.line_buffer.get(index)
            collector.add(index, len(raw_line) - len(text), text)

        source = collector.map()
        if source is None:
            return None
        raw_text = ''.join(lines)
        start = len(raw_text) - len(raw_text.lstrip())
        end = len(raw_text.rstrip())
        return source.slice(start, end)
