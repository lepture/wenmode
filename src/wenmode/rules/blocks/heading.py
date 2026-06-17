from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Heading, Node
from wenmode.rules.base import BlockRule, Rule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


ATX_HEADING_RE = re.compile(r'[ \t]{0,3}(#{1,6})(?:[ \t]+|$)(.*?)(?:[ \t]+#+[ \t]*)?$')
SETEXT_HEADING_RE = re.compile(r'[ \t]{0,3}(=+|-+)[ \t]*$')


class AtxHeading(BlockRule):
    def __init__(self) -> None:
        super().__init__('atx_heading', r'[ \t]{0,3}#{1,6}(?:[ \t]+|$)')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Heading:
        line = state.line.rstrip('\r\n')
        heading = ATX_HEADING_RE.match(line)
        if heading is None:
            state.advance()
            return Heading(children=[])

        marker, content = heading.groups()
        if content.strip('#').strip() == '':
            content = ''
        state.advance()
        return Heading(depth=len(marker), children=parser.parse_inlines(content.strip(), state))


class SetextHeading(Rule):
    def __init__(self) -> None:
        super().__init__('setext_heading')

    def parse_paragraph_continuation(
        self, parser: Parser, state: BlockState, lines: list[str]
    ) -> Node | None:
        marker = SETEXT_HEADING_RE.match(state.line)
        if marker is None:
            return None

        state.advance()
        depth = 1 if marker.group(1).startswith('=') else 2
        text = ''.join(lines).strip()
        return Heading(depth=depth, children=parser.parse_inlines(text, state))
