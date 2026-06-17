from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import InlineMath as InlineMathNode
from wenmode.nodes import Node
from wenmode.state import BlockState

from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


class InlineMath(InlineRule):
    def __init__(self) -> None:
        super().__init__('inline_math', r'\$', '$')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        start = match.start()
        if is_escaped(text, start) or is_adjacent_to_dollar(text, start) or is_opening_space(text, start):
            return None, start

        end = find_closing_dollar(text, match.end())
        if end is None:
            return None, start

        value = text[match.end() : end]
        if value.strip() == '':
            return None, start
        return InlineMathNode(value=value), end + 1


def find_closing_dollar(text: str, start: int) -> int | None:
    index = start
    while index < len(text):
        char = text[index]
        if char in '\r\n':
            return None
        if char == '$' and not is_escaped(text, index) and not is_adjacent_closing_dollar(text, index):
            if is_closing_space(text, index) or is_closing_before_digit(text, index):
                index += 1
                continue
            return index
        index += 1
    return None


def is_opening_space(text: str, index: int) -> bool:
    return index + 1 >= len(text) or text[index + 1].isspace()


def is_closing_space(text: str, index: int) -> bool:
    return index == 0 or text[index - 1].isspace()


def is_closing_before_digit(text: str, index: int) -> bool:
    return index + 1 < len(text) and text[index + 1].isdigit()


def is_adjacent_closing_dollar(text: str, index: int) -> bool:
    previous_is_unescaped_dollar = index > 0 and text[index - 1] == '$' and not is_escaped(text, index - 1)
    next_is_dollar = index + 1 < len(text) and text[index + 1] == '$'
    return previous_is_unescaped_dollar or next_is_dollar


def is_adjacent_to_dollar(text: str, index: int) -> bool:
    previous_is_dollar = index > 0 and text[index - 1] == '$'
    next_is_dollar = index + 1 < len(text) and text[index + 1] == '$'
    return previous_is_dollar or next_is_dollar


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == '\\':
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1
