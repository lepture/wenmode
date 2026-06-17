from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import BlockSpoiler as BlockSpoilerNode
from wenmode.state import BlockState
from wenmode.utils import expand_leading_tabs

from ..base import BlockRule
from .util import parse_shallow_block

if TYPE_CHECKING:
    from wenmode.parser import Parser


BLOCK_SPOILER_RE = re.compile(r'[ \t]{0,3}>! ?(.*)')


class BlockSpoiler(BlockRule):
    order = 90

    def __init__(self) -> None:
        super().__init__('block_spoiler', r'[ \t]{0,3}>!')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> BlockSpoilerNode:
        if state.depth >= parser.max_container_depth - 1:
            return BlockSpoilerNode(children=parse_shallow_block(parser, BLOCK_SPOILER_RE, state))

        lines: list[str] = []
        while not state.done:
            spoiler = BLOCK_SPOILER_RE.match(state.line)
            if spoiler is None:
                break
            line_end = '\n' if state.line.endswith('\n') else ''
            lines.append(expand_leading_tabs(spoiler.group(1), 2) + line_end)
            state.advance()

        return BlockSpoilerNode(children=parser.parse_blocks(''.join(lines), parent_state=state))
