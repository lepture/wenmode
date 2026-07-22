from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import Node
from wenmode.nodes import TextDirective as TextDirectiveNode
from wenmode.rules import InlineCandidate, InlineRule
from wenmode.rules.inlines.directive import NAME_RE

from .._parser.state import BlockState

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


class RoleRule(InlineRule):
    """Parse MyST-style inline roles."""

    name = 'role'
    pattern = r'\{(?=[A-Za-z])'
    opener = '{'

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        start = candidate.start
        parsed = _parse_role(text, start)
        if parsed is None:
            return None, start

        name, label, end, label_start, label_end = parsed
        return (
            TextDirectiveNode(
                name=name,
                children=parser.parse_inlines(
                    label, state, source=parser.inline_source(text, state, label_start, label_end)
                ),
            ),
            end,
        )


def _parse_role(text: str, start: int) -> tuple[str, str, int, int, int] | None:
    name_end = text.find('}', start + 1)
    if name_end == -1:
        return None
    name = text[start + 1 : name_end]
    if NAME_RE.fullmatch(name) is None:
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

    return name, text[tick_end:closing], closing + len(fence), tick_end, closing


nodes: dict[str, type[Node]] = {}


def setup(wen: Wenmode, /) -> None:
    wen.register_rule(RoleRule)
