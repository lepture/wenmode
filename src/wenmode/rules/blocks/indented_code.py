from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Code
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


class IndentedCode(BlockRule):
    def __init__(self) -> None:
        super().__init__('indented_code', r'(?: {4,}|[ \t]{0,3}\t)')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Code:
        lines: list[str] = []

        while not state.done:
            line = state.line
            if not has_indent(line, 4):
                if line.strip() == '':
                    lines.append('\n')
                    state.advance()
                    continue
                break
            lines.append(strip_indent(line, 4))
            state.advance()

        while lines and lines[-1] == '\n':
            lines.pop()

        return Code(value=''.join(lines))


def has_indent(line: str, columns: int) -> bool:
    column = 0
    for char in line:
        if char == ' ':
            column += 1
        elif char == '\t':
            column += 4 - column % 4
        else:
            break
        if column >= columns:
            return True
    return False


def strip_indent(line: str, columns: int) -> str:
    column = 0
    index = 0
    while index < len(line) and column < columns:
        char = line[index]
        if char == ' ':
            column += 1
        elif char == '\t':
            column += 4 - column % 4
        else:
            break
        index += 1
    if column > columns:
        return ' ' * (column - columns) + line[index:]
    return line[index:]
