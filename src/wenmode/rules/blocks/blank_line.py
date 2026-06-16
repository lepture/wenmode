from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


class BlankLine(BlockRule):
    def __init__(self) -> None:
        super().__init__('blank_line', r'[ \t]*(?:\r?\n)?$')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Node | None:
        state.advance()
        return None
