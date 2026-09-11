from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import Code
from wenmode.utils import count_indent_from, count_indent_width

from ..._parser.rule_base import BlockCandidate, BlockRule
from ..._parser.state import BlockState

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
            if count_indent_from(line) < 4:
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
    width, index = count_indent_width(line, columns)
    if width > columns:
        return ' ' * (width - columns) + line[index:]
    return line[index:]
