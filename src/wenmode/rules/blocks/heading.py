from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Heading
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


class AtxHeading(BlockRule):
    def __init__(self) -> None:
        super().__init__('atx_heading', r'[ \t]{0,3}#{1,6}(?:[ \t]+|$)')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Heading:
        line = state.line.rstrip('\r\n')
        heading = re.match(r'[ \t]{0,3}(#{1,6})(?:[ \t]+|$)(.*?)(?:[ \t]+#+[ \t]*)?$', line)
        if heading is None:
            state.advance()
            return Heading(children=[])

        marker, content = heading.groups()
        if content.strip('#').strip() == '':
            content = ''
        state.advance()
        return Heading(depth=len(marker), children=parser.parse_inlines(content.strip(), state))
