from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Math, Node
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


MATH_OPENER_RE = re.compile(r'^[ \t]{0,3}\$\$[ \t]*(?P<rest>.*?)(?:\r?\n)?$')
MATH_CLOSER_RE = re.compile(r'^[ \t]{0,3}\$\$[ \t]*(?:\r?\n)?$')


class MathBlock(BlockRule):
    def __init__(self) -> None:
        super().__init__('math_block', r'[ \t]{0,3}\$\$')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node:
        opener = MATH_OPENER_RE.match(state.line)
        if opener is None:
            state.advance()
            return Math(value='')

        lines: list[str] = []
        rest = opener.group('rest')
        if rest:
            lines.append(rest + '\n')
        state.advance()

        while not state.done:
            if MATH_CLOSER_RE.match(state.line):
                state.advance()
                break
            lines.append(state.line)
            state.advance()

        return Math(value=''.join(lines))
