from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import ThematicBreak as ThematicBreakNode
from wenmode.state import BlockState

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

    def __init__(self) -> None:
        super().__init__(
            'thematic_break', r'[ \t]{0,3}(?:\*[ \t]*){3,}$|[ \t]{0,3}(?:-[ \t]*){3,}$|[ \t]{0,3}(?:_[ \t]*){3,}$'
        )

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> ThematicBreakNode:
        state.advance()
        return ThematicBreakNode()
