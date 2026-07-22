from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import Delete, Node

from ..._parser.state import BlockState
from ..base import InlineRule
from ..delimiters import find_delimited_span

if TYPE_CHECKING:
    from wenmode.parser import Parser


class Strikethrough(InlineRule):
    """Parse deletion spans delimited by tildes.

    Markdown syntax:

    .. code-block:: markdown

       ~~deleted~~
    """

    name = 'strikethrough'
    opener = '~'

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        parsed = find_delimited_span(text, start, '~', max_run=2, reject_adjacent=True)
        if parsed is None:
            return None, start

        value = text[parsed.value_start : parsed.value_end]
        return Delete(
            children=parser.parse_inlines(
                value, state, source=parser.inline_source(text, state, parsed.value_start, parsed.value_end)
            )
        ), parsed.close_end
