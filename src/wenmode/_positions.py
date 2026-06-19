from __future__ import annotations

from .nodes import Point, Position


def advance_point(point: Point, text: str) -> Point:
    """Return the point reached after consuming ``text``."""
    line = point.line
    column = point.column
    offset = point.offset
    for char in text:
        offset += 1
        if char == '\n':
            line += 1
            column = 1
        else:
            column += 1
    return Point(line=line, column=column, offset=offset)


def position_from_offsets(position: Position | None, text: str, start: int, end: int) -> Position | None:
    """Return a position for ``text[start:end]`` within an existing position."""
    if position is None:
        return None
    start_point = advance_point(position.start, text[:start])
    end_point = advance_point(start_point, text[start:end])
    return Position(start=start_point, end=end_point)
