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

    __slots__ = (
        '_contiguous_segments',
        '_direct_slice_offsets',
        '_segment_ends',
        '_segment_starts',
        '_text_length',
        'segments',
        'text',
    )

    def __init__(self, text: str, segments: list[SourceSegment]) -> None:
        self.text = text
        self._text_length = len(text)
        self.segments = segments
        if len(segments) < 2:
            self._direct_slice_offsets = True
            self._contiguous_segments = True
            self._segment_starts = tuple(segment.start for segment in segments)
            self._segment_ends = tuple(segment.end for segment in segments)
            return
        starts = tuple(segment.start for segment in segments)
        ends = tuple(segment.end for segment in segments)
        ordered = all(left <= right for left, right in zip(starts, starts[1:])) and all(
            left <= right for left, right in zip(ends, ends[1:])
        )
        self._direct_slice_offsets = ordered and all(
            left.end <= right.start for left, right in zip(segments, segments[1:])
        )
        self._contiguous_segments = ordered and all(
            left.end == right.start for left, right in zip(segments, segments[1:])
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
        if len(parts) == 1:
            text, source_offset = parts[0]
            return cls.contiguous(text, source_offset)

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
        if len(self.segments) == 1:
            segment = self.segments[0]
            if segment.start == 0 and segment.end == self._text_length:
                return SourceMap.contiguous(text, segment.offset + start)

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
            segments.append(SourceSegment(start=segment_start - start, end=segment_end - start, offset=source_offset))
        if not segments:
            segments.append(SourceSegment(0, 0, self.source_offset(start)))
        return SourceMap(text, segments)

    def line_offsets(self, lines: list[str]) -> list[int]:
        if self._contiguous_segments and self.segments:
            return self._contiguous_line_offsets(lines)

        offsets: list[int] = []
        offset = 0
        for line in lines:
            offsets.append(self.source_offset(offset))
            offset += len(line)
        return offsets

    def _contiguous_line_offsets(self, lines: list[str]) -> list[int]:
        offsets: list[int] = []
        source_index = 0
        segments = self.segments
        offset = 0
        for line in lines:
            while source_index + 1 < len(segments) and offset >= segments[source_index + 1].start:
                source_index += 1
            segment = segments[source_index]
            if offset <= segment.start:
                offsets.append(segment.offset)
            elif offset <= segment.end:
                offsets.append(segment.offset + offset - segment.start)
            else:
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

    __slots__ = ('_source_ends', '_source_offsets', '_text_parts', 'tracker')

    def __init__(self, tracker: PositionSourceTracker) -> None:
        self.tracker = tracker
        self._text_parts: list[list[str]] = []
        self._source_offsets: list[int] = []
        self._source_ends: list[int] = []

    def add(self, index: int, offset: int, text: str) -> None:
        source_offset = self.tracker.collect_offset_at_line_offset(index, offset)
        if source_offset is not None:
            source_end = source_offset + len(text)
            if self._source_ends and self._source_ends[-1] == source_offset:
                self._text_parts[-1].append(text)
                self._source_ends[-1] = source_end
            else:
                self._text_parts.append([text])
                self._source_offsets.append(source_offset)
                self._source_ends.append(source_end)

    def map(self) -> SourceMap | None:
        if not self._text_parts:
            return None
        if len(self._text_parts) == 1:
            return SourceMap.contiguous(''.join(self._text_parts[0]), self._source_offsets[0])
        return SourceMap.from_parts(
            [
                (''.join(text_parts), source_offset)
                for text_parts, source_offset in zip(self._text_parts, self._source_offsets)
            ]
        )


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

    def collect_offset_at_line_offset(self, index: int, offset: int) -> int | None:
        return self.offset_at_line_offset(index, offset)

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


def _paragraph_source_from_parts(parts: list[tuple[str, int]]) -> SourceMap | None:
    if not parts:
        return None

    raw_text = ''.join(text for text, _source_offset in parts)
    start = len(raw_text) - len(raw_text.lstrip())
    end = len(raw_text.rstrip())
    text = raw_text[start:end]
    if len(parts) == 1:
        return SourceMap.contiguous(text, parts[0][1] + start)

    segments: list[SourceSegment] = []
    offset = 0
    for part_text, source_offset in parts:
        part_start = offset
        part_end = offset + len(part_text)
        offset = part_end
        if part_end < start or part_start > end:
            continue
        segment_start = max(part_start, start)
        segment_end = min(part_end, end)
        if segment_start > segment_end:
            continue
        segments.append(
            SourceSegment(
                start=segment_start - start,
                end=segment_end - start,
                offset=source_offset + segment_start - part_start,
            )
        )

    if not segments:
        segments.append(SourceSegment(0, 0, parts[0][1]))
    return SourceMap(text, segments)


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

    def collect_offset_at_line_offset(self, index: int, offset: int) -> int | None:
        if 0 <= index < len(self.line_offsets):
            source_offset = self.line_offsets[index]
            if offset > 0:
                source_offset += offset
            return source_offset
        return self.offset_at_line_offset(index, offset)

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
        parts: list[tuple[str, int]] = []
        for offset, text in enumerate(lines):
            index = start_index + offset
            if index < 0 or index >= len(state.lines):
                return None
            raw_line = state.line_at(index)
            source_offset = self.offset_at_line_offset(index, len(raw_line) - len(text))
            if source_offset is not None:
                parts.append((text, source_offset))
        return _paragraph_source_from_parts(parts)

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

    def collect_offset_at_line_offset(self, index: int, offset: int) -> int | None:
        source_offset = self.line_buffer.offset_at_index(index)
        if offset > 0:
            source_offset += offset
        return source_offset

    def paragraph(self, lines: list[str], start_index: int) -> SourceMap | None:
        parts: list[tuple[str, int]] = []
        for offset, text in enumerate(lines):
            index = start_index + offset
            raw_line = self.line_buffer.get(index)
            source_offset = self.offset_at_line_offset(index, len(raw_line) - len(text))
            if source_offset is not None:
                parts.append((text, source_offset))
        return _paragraph_source_from_parts(parts)
