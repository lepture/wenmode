from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import BlockSpoiler as BlockSpoilerNode
from wenmode.nodes import Point
from wenmode.state import BlockState
from wenmode.utils import expand_leading_tabs

from ..base import BlockRule
from .util import parse_shallow_block

if TYPE_CHECKING:
    from wenmode.parser import Parser


BLOCK_SPOILER_RE = re.compile(r'[ \t]{0,3}>! ?(.*)')


class BlockSpoiler(BlockRule):
    """Parse ``>!`` block spoiler containers.

    Markdown syntax:

    .. code-block:: markdown

       >! hidden text
    """

    order = 90

    def __init__(self) -> None:
        super().__init__('block_spoiler', r'[ \t]{0,3}>!')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> BlockSpoilerNode:
        if state.depth >= parser.max_container_depth - 1:
            return BlockSpoilerNode(children=parse_shallow_block(parser, BLOCK_SPOILER_RE, state))

        lines: list[str] = []
        source_parts: list[tuple[str, Point]] = []
        while not state.done:
            spoiler = BLOCK_SPOILER_RE.match(state.line)
            if spoiler is None:
                break
            line_end = '\n' if state.line.endswith('\n') else ''
            text = expand_leading_tabs(spoiler.group(1), 2) + line_end
            lines.append(text)
            point = state.point_at_line_offset(state.index, spoiler.start(1))
            if point is not None:
                source_parts.append((text, point))
            state.advance()

        text = ''.join(lines)
        return BlockSpoilerNode(
            children=parser.parse_blocks(text, parent_state=state, source=parser.source_map_from_parts(source_parts))
        )
