from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import Code
from wenmode.utils import count_indent

from ..._parser.state import BlockState
from ..base import BlockCandidate, BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


class IndentedCode(BlockRule):
    """Parse indented code blocks.

    Markdown syntax:

    .. code-block:: markdown

           print(1)
    """

    name = 'indented_code'
    pattern = r'(?: {4,}|[ \t]{0,3}\t)'

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Code:
        lines: list[str] = []

        while not state.done:
            line = state.line
            if count_indent(line) < 4:
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
