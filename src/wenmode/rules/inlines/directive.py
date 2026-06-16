from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node
from wenmode.nodes import TextDirective as TextDirectiveNode
from wenmode.rules.base import InlineRule
from wenmode.rules.directives import parse_directive_head
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


ROLE_NAME_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]*')


class TextDirective(InlineRule):
    def __init__(self) -> None:
        super().__init__('text_directive', r':(?=[A-Za-z])', ':')

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        parsed = parse_directive_head(text, match.start() + 1)
        if parsed is None:
            return None, match.start()

        name, label, attributes, end = parsed
        children = parser.parse_inlines(label, state) if label is not None else []
        return TextDirectiveNode(name=name, attributes=attributes, children=children), end


class Role(InlineRule):
    def __init__(self) -> None:
        super().__init__('role', r'\{(?=[A-Za-z])', '{')

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        parsed = parse_role(text, match.start())
        if parsed is None:
            return None, match.start()

        name, label, end = parsed
        return TextDirectiveNode(name=name, children=parser.parse_inlines(label, state)), end


def parse_role(text: str, start: int = 0) -> tuple[str, str, int] | None:
    if start >= len(text) or text[start] != '{':
        return None

    name_end = text.find('}', start + 1)
    if name_end == -1:
        return None
    name = text[start + 1 : name_end]
    if ROLE_NAME_RE.fullmatch(name) is None:
        return None

    tick_start = name_end + 1
    if tick_start >= len(text) or text[tick_start] != '`':
        return None

    tick_end = tick_start
    while tick_end < len(text) and text[tick_end] == '`':
        tick_end += 1
    fence = text[tick_start:tick_end]
    closing = text.find(fence, tick_end)
    if closing == -1:
        return None

    return name, text[tick_end:closing], closing + len(fence)
