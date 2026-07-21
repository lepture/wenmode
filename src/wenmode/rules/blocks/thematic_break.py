from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import ThematicBreak as ThematicBreakNode

from ..._parser.state import BlockState
from ..base import BlockRule

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
        r'[ \t]{0,3}\*[ \t]*\*[ \t]*\*[ \t*]*$'
        r'|[ \t]{0,3}-[ \t]*-[ \t]*-[ \t-]*$'
        r'|[ \t]{0,3}_[ \t]*_[ \t]*_[ \t_]*$'
    )

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> ThematicBreakNode:
        state.advance()
        return ThematicBreakNode()
