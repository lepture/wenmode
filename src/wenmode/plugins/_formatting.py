from __future__ import annotations

from wenmode.utils import is_escaped


def find_closing_marker(text: str, start: int, marker: str) -> int:
    delimiter = marker * 2
    index = text.find(delimiter, start)
    while index != -1:
        if is_closing_marker(text, index, marker):
            return index
        index = text.find(delimiter, index + 1)
    return -1


def is_closing_marker(text: str, start: int, marker: str) -> bool:
    return (
        not is_escaped(text, start)
        and not is_part_of_longer_run(text, start, marker)
        and start > 0
        and not text[start - 1].isspace()
        and text[start - 1] != marker
    )


def is_part_of_longer_run(text: str, start: int, marker: str) -> bool:
    return (start > 0 and text[start - 1] == marker) or (start + 2 < len(text) and text[start + 2] == marker)
