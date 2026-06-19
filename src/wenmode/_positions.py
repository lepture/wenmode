from __future__ import annotations

from .nodes import Point, Position


def advance_point(point: Point, text: str) -> Point:
    """Return the point reached after consuming ``text``."""
    text_length = len(text)
    if text_length == 0:
        return point

    offset = point.offset + text_length
    first_line_break = text.find('\n')
    if first_line_break == -1:
        return Point(line=point.line, column=point.column + text_length, offset=offset)

    line_breaks = text.count('\n')
    last_line_break = text.rfind('\n')
    return Point(line=point.line + line_breaks, column=text_length - last_line_break, offset=offset)


def position_from_offsets(position: Position | None, text: str, start: int, end: int) -> Position | None:
    """Return a position for ``text[start:end]`` within an existing position."""
    if position is None:
        return None
    start_point = advance_point(position.start, text[:start])
    end_point = advance_point(start_point, text[start:end])
    return Position(start=start_point, end=end_point)
