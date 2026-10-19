from __future__ import annotations

from bisect import bisect_left
from dataclasses import dataclass

from wenmode._parser.state import BlockState
from wenmode._parser.store import StateKey
from wenmode.utils import is_escaped

DELIMITER_POSITIONS = StateKey[dict[tuple[int, str, bool], tuple[str, list[int]]]](
    'wenmode.delimiter.positions', lambda: {}
)
DELIMITER_SPACES = StateKey[dict[tuple[int, bool], tuple[str, list[int]]]]('wenmode.delimiter.spaces', lambda: {})


@dataclass(frozen=True, slots=True)
class DelimitedSpan:
    opener: str
    value_start: int
    value_end: int
    close_end: int


def find_delimited_span(
    text: str,
    start: int,
    delimiter: str,
    *,
    max_run: int = 1,
    reject_adjacent: bool = False,
    allow_spaces: bool = True,
    allow_escaped_space: bool = False,
    state: BlockState | None = None,
) -> DelimitedSpan | None:
    opener = opening_delimiter(text, start, delimiter, max_run=max_run, reject_adjacent=reject_adjacent)
    if opener is None:
        return None

    value_start = start + len(opener)
    close = find_closing_delimiter(
        text,
        value_start,
        opener,
        reject_adjacent=reject_adjacent,
        allow_spaces=allow_spaces,
        allow_escaped_space=allow_escaped_space,
        state=state,
    )
    if close is None or close == value_start:
        return None
    return DelimitedSpan(opener=opener, value_start=value_start, value_end=close, close_end=close + len(opener))


def opening_delimiter(text: str, start: int, delimiter: str, *, max_run: int, reject_adjacent: bool) -> str | None:
    if start >= len(text) or text[start] != delimiter:
        return None

    size = 1
    while size < max_run and start + size < len(text) and text[start + size] == delimiter:
        size += 1

    if reject_adjacent and is_part_of_longer_run(text, start, delimiter, size):
        return None
    return delimiter * size


def find_closing_delimiter(
    text: str,
    start: int,
    delimiter: str,
    *,
    reject_adjacent: bool,
    allow_spaces: bool,
    allow_escaped_space: bool,
    state: BlockState | None = None,
) -> int | None:
    if state is not None:
        cache = state.store.get(DELIMITER_POSITIONS)
        key = (id(text), delimiter, reject_adjacent)
        cached = cache.get(key)
        if cached is None or cached[0] is not text:
            positions: list[int] = []
            close = text.find(delimiter)
            while close != -1:
                if not is_escaped(text, close) and not (
                    reject_adjacent and is_part_of_longer_run(text, close, delimiter[0], len(delimiter))
                ):
                    positions.append(close)
                close = text.find(delimiter, close + 1)
            cache[key] = (text, positions)
        else:
            positions = cached[1]
        index = bisect_left(positions, start)
        if index == len(positions):
            return None
        close = positions[index]
        if not allow_spaces:
            spaces_cache = state.store.get(DELIMITER_SPACES)
            spaces_key = (id(text), allow_escaped_space)
            spaces = spaces_cache.get(spaces_key)
            if spaces is None or spaces[0] is not text:
                rejected = [
                    index
                    for index, char in enumerate(text)
                    if (
                        (char == ' ' and (index == 0 or text[index - 1] != '\\'))
                        if allow_escaped_space
                        else char.isspace()
                    )
                ]
                spaces_cache[spaces_key] = (text, rejected)
            else:
                rejected = spaces[1]
            index = bisect_left(rejected, start)
            if (allow_escaped_space and start < close and text[start] == ' ') or (
                index < len(rejected) and rejected[index] < close
            ):
                return None
        return close
    index = start
    while index < len(text):
        close = text.find(delimiter, index)
        if (
            not allow_spaces
            and first_rejected_space(text, index, close if close != -1 else len(text), allow_escaped_space) is not None
        ):
            return None
        if close == -1:
            return None
        if not is_escaped(text, close) and not (
            reject_adjacent and is_part_of_longer_run(text, close, delimiter[0], len(delimiter))
        ):
            return close
        index = close + 1
    return None


def first_rejected_space(text: str, start: int, end: int, allow_escaped_space: bool) -> int | None:
    if allow_escaped_space:
        index = start
        while True:
            index = text.find(' ', index, end)
            if index == -1:
                return None
            if index == start or text[index - 1] != '\\':
                return index
            index += 1
    for index in range(start, end):
        if text[index].isspace():
            return index
    return None


def is_part_of_longer_run(text: str, start: int, delimiter: str, size: int) -> bool:
    return (start > 0 and text[start - 1] == delimiter) or (start + size < len(text) and text[start + size] == delimiter)
