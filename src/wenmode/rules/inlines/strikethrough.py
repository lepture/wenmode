from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import Delete, Node

from ..._parser.rule_base import InlineCandidate, InlineRule
from ..._parser.state import BlockState
from ..delimiters import find_delimited_span

if TYPE_CHECKING:
    from wenmode.parser import Parser


class Strikethrough(InlineRule):
    """Parse deletion spans delimited by tildes.

    :param allow_single_tilde: Parse single-tilde spans in addition to
        double-tilde spans.

    Markdown syntax:

    .. code-block:: markdown

       ~~deleted~~
    """

    name = 'strikethrough'
    opener = '~'

    def __init__(self, allow_single_tilde: bool = True) -> None:
        super().__init__()
        self.allow_single_tilde = allow_single_tilde

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        start = candidate.start
        if not self.allow_single_tilde and not text.startswith('~~', start):
            return None, start
        parsed = find_delimited_span(text, start, '~', max_run=2, reject_adjacent=True)
        if parsed is None:
            return None, start

        value = text[parsed.value_start : parsed.value_end]
        return Delete(
            children=parser.parse_inlines(
                value, state, source=parser.inline_source(text, state, parsed.value_start, parsed.value_end)
            )
        ), parsed.close_end
