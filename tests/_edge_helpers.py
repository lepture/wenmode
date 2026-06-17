from __future__ import annotations

import re
from dataclasses import dataclass

from wenmode import HTMLRenderer, Parser
from wenmode.nodes import Node, Text
from wenmode.rules import InlineRule
from wenmode.state import BlockState


@dataclass
class WrapperNode(Node):
    child: Node | None = None
    children: list[Node] | None = None
    value: str | None = None
    type: str = 'wrapper'


@dataclass
class IdentifierNode(Node):
    identifier: str = ''
    type: str = 'identifier'


class SearchInline(InlineRule):
    order = 10

    def __init__(self) -> None:
        super().__init__('search_inline', r'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='search'), match.end()


class LaterSearchInline(InlineRule):
    order = 20

    def __init__(self) -> None:
        super().__init__('later_search_inline', r'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='later'), match.end()


class TriggerInline(InlineRule):
    order = 30

    def __init__(self) -> None:
        super().__init__('trigger_inline', r'x', 'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='trigger'), match.end()


def render_html(parser: Parser, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))
