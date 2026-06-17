from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Mark as MarkNode
from wenmode.nodes import Node
from wenmode.state import BlockState

from ..base import InlineRule
from .strikethrough import is_escaped

if TYPE_CHECKING:
    from wenmode.parser import Parser


class Mark(InlineRule):
    def __init__(self) -> None:
        super().__init__('mark', r'==(?=[^\s=])', '=')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        start = match.start()
        if is_part_of_longer_run(text, start):
            return None, start

        close = find_closing_marker(text, match.end())
        if close == -1:
            return None, start

        value = text[match.end() : close]
        return MarkNode(children=parser.parse_inlines(value, state)), close + 2


def find_closing_marker(text: str, start: int) -> int:
    index = text.find('==', start)
    while index != -1:
        if is_closing_marker(text, index):
            return index
        index = text.find('==', index + 1)
    return -1


def is_closing_marker(text: str, start: int) -> bool:
    return (
        not is_escaped(text, start)
        and not is_part_of_longer_run(text, start)
        and start > 0
        and not text[start - 1].isspace()
        and text[start - 1] != '='
    )


def is_part_of_longer_run(text: str, start: int) -> bool:
    return (start > 0 and text[start - 1] == '=') or (start + 2 < len(text) and text[start + 2] == '=')
