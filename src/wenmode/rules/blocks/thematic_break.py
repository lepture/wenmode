from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import ThematicBreak as ThematicBreakNode
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


class ThematicBreak(BlockRule):
    def __init__(self) -> None:
        super().__init__(
            'thematic_break', r'[ \t]{0,3}(?:\*[ \t]*){3,}$|[ \t]{0,3}(?:-[ \t]*){3,}$|[ \t]{0,3}(?:_[ \t]*){3,}$'
        )

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> ThematicBreakNode:
        state.advance()
        return ThematicBreakNode()
