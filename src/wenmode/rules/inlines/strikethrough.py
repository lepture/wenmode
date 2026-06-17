from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Delete, Node
from wenmode.state import BlockState

from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


class Strikethrough(InlineRule):
    def __init__(self) -> None:
        super().__init__('strikethrough', r'~{1,2}', '~')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        marker = match.group(0)
        start = match.start()
        if is_part_of_longer_run(text, start, len(marker)):
            return None, start

        close = find_closing_marker(text, marker, match.end())
        if close == -1:
            return None, start

        value = text[match.end() : close]
        if value == '':
            return None, start
        return Delete(children=parser.parse_inlines(value, state)), close + len(marker)


def find_closing_marker(text: str, marker: str, start: int) -> int:
    index = text.find(marker, start)
    while index != -1:
        if not is_escaped(text, index) and not is_part_of_longer_run(text, index, len(marker)):
            return index
        index = text.find(marker, index + 1)
    return -1


def is_part_of_longer_run(text: str, start: int, size: int) -> bool:
    return (start > 0 and text[start - 1] == '~') or (start + size < len(text) and text[start + size] == '~')


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == '\\':
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1
