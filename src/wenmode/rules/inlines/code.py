from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import InlineCode as InlineCodeNode
from wenmode.nodes import Node, Text

from ..._parser.state import BlockState
from ..base import InlineCandidate, InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


CODE_LINE_ENDING_RE = re.compile(r'\r\n?|\n')
BACKTICK_RUN_RE = re.compile(r'`+')


class InlineCode(InlineRule):
    """Parse inline code spans.

    Markdown syntax:

    .. code-block:: markdown

       `code`
    """

    name = 'inline_code'
    opener = '`'

    def match_candidate(self, text: str, start: int) -> InlineCandidate | None:
        if text[start] != '`' or (start > 0 and text[start - 1] == '`'):
            return None
        match = BACKTICK_RUN_RE.match(text, start)
        if match is None:
            return None
        return InlineCandidate(start, match)

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        start = candidate.start
        match = candidate.match
        assert match is not None
        marker_length = match.end() - start
        value_start = match.end()
        end = find_matching_backtick_run(text, value_start, marker_length)
        if end is None:
            return Text(value=text[start:value_start]), value_start
        value = CODE_LINE_ENDING_RE.sub(' ', text[value_start:end])
        if len(value) >= 2 and value.startswith(' ') and value.endswith(' ') and any(char != ' ' for char in value):
            value = value[1:-1]
        return InlineCodeNode(value=value), end + marker_length


def find_matching_backtick_run(text: str, start: int, marker_length: int) -> int | None:
    """Return the next backtick run with exactly ``marker_length`` characters."""
    for run in BACKTICK_RUN_RE.finditer(text, start):
        if run.end() - run.start() == marker_length:
            return run.start()
    return None
