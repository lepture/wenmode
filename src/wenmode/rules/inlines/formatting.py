from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Insert as InsertNode
from wenmode.nodes import Mark as MarkNode
from wenmode.nodes import Node
from wenmode.nodes import Superscript as SuperscriptNode
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
        if is_part_of_longer_run(text, start, '='):
            return None, start

        close = find_closing_marker(text, match.end(), '=')
        if close == -1:
            return None, start

        value = text[match.end() : close]
        return MarkNode(children=parser.parse_inlines(value, state)), close + 2


class Insert(InlineRule):
    def __init__(self) -> None:
        super().__init__('insert', r'\^\^(?=[^\s\^])', '^')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        start = match.start()
        if is_part_of_longer_run(text, start, '^'):
            return None, start

        close = find_closing_marker(text, match.end(), '^')
        if close == -1:
            return None, start

        value = text[match.end() : close]
        return InsertNode(children=parser.parse_inlines(value, state)), close + 2


class Superscript(InlineRule):
    def __init__(self) -> None:
        super().__init__('superscript', r'\^(?:(?<!\\)(?:\\\\)*\\\^|\S|\\ )+?\^', '^')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        value = match.group(0)[1:-1].replace('\\ ', ' ')
        return SuperscriptNode(children=parser.parse_inlines(value, state)), match.end()


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
