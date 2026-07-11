from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Delete, Node
from wenmode.utils import is_escaped

from ..._parser.state import BlockState
from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


class Strikethrough(InlineRule):
    """Parse deletion spans delimited by tildes.

    Markdown syntax:

    .. code-block:: markdown

       ~~deleted~~
    """

    name = 'strikethrough'
    pattern = r'~{1,2}'
    trigger_chars = '~'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        marker = match.group(0)
        start = match.start()
        if is_part_of_longer_run(text, start, len(marker)):
            return None, start

        close = find_closing_marker(text, marker, match.end())
        if close == -1:
            return None, start

        value_start = match.end()
        value = text[value_start:close]
        if value == '':
            return None, start
        return Delete(
            children=parser.parse_inlines(value, state, source=parser.inline_source(text, state, value_start, close))
        ), close + len(marker)


def find_closing_marker(text: str, marker: str, start: int) -> int:
    index = text.find(marker, start)
    while index != -1:
        if not is_escaped(text, index) and not is_part_of_longer_run(text, index, len(marker)):
            return index
        index = text.find(marker, index + 1)
    return -1


def is_part_of_longer_run(text: str, start: int, size: int) -> bool:
    return (start > 0 and text[start - 1] == '~') or (start + size < len(text) and text[start + size] == '~')
