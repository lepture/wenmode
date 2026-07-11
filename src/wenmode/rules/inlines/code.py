from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import InlineCode as InlineCodeNode
from wenmode.nodes import Node

from ..._parser.state import BlockState
from ..base import InlineRule

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
    pattern = r'(?<!`)`+'
    trigger_chars = '`'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        if match.start() > 0 and text[match.start() - 1] == '`':
            return None, match.start()
        marker_length = match.end() - match.start()
        end = find_matching_backtick_run(text, match.end(), marker_length)
        if end is None:
            return None, match.start()
        value = CODE_LINE_ENDING_RE.sub(' ', text[match.end() : end])
        if len(value) >= 2 and value.startswith(' ') and value.endswith(' ') and any(char != ' ' for char in value):
            value = value[1:-1]
        return InlineCodeNode(value=value), end + marker_length


def find_matching_backtick_run(text: str, start: int, marker_length: int) -> int | None:
    """Return the next backtick run with exactly ``marker_length`` characters."""
    for run in BACKTICK_RUN_RE.finditer(text, start):
        if run.end() - run.start() == marker_length:
            return run.start()
    return None
