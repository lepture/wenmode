from __future__ import annotations

from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import ThematicBreak as ThematicBreakNode

from ..._parser.state import BlockState
from ..base import BlockCandidate, BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


class ThematicBreak(BlockRule):
    """Parse thematic breaks such as ``---``, ``***``, and ``___``.

    Markdown syntax:

    .. code-block:: markdown

       ---
    """

    order: ClassVar[int] = 50
    name = 'thematic_break'
    pattern = (
        r' {0,3}\*[ \t]*\*[ \t]*\*[ \t*]*$'
        r'| {0,3}-[ \t]*-[ \t]*-[ \t-]*$'
        r'| {0,3}_[ \t]*_[ \t]*_[ \t_]*$'
    )

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> ThematicBreakNode:
        state.advance()
        return ThematicBreakNode()
