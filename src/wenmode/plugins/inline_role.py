from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import Node
from wenmode.nodes import TextDirective as TextDirectiveNode
from wenmode.rules import InlineCandidate, InlineRule
from wenmode.rules.inlines.code import BACKTICK_RUN_RE
from wenmode.rules.inlines.directive import NAME_RE
from wenmode.state import BlockState, StateKey

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


ROLE_RUNS = StateKey[dict[int, tuple[str, dict[int, int | None]]]]('wenmode.role.runs', lambda: {})


class RoleRule(InlineRule):
    """Parse MyST-style inline roles."""

    name = 'role'
    pattern = r'\{(?=[A-Za-z])'
    opener = '{'

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        start = candidate.start
        parsed = _parse_role(text, start, state)
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


def _parse_role(text: str, start: int, state: BlockState | None = None) -> tuple[str, str, int, int, int] | None:
    match = NAME_RE.match(text, start + 1)
    if match is None or match.end() >= len(text) or text[match.end()] != '}':
        return None
    name = match.group()
    name_end = match.end()

    tick_start = name_end + 1
    if tick_start >= len(text) or text[tick_start] != '`':
        return None

    tick_end = tick_start
    while tick_end < len(text) and text[tick_end] == '`':
        tick_end += 1
    fence = text[tick_start:tick_end]
    cached = state.store.get(ROLE_RUNS).get(id(text)) if state is not None else None
    if cached is not None and cached[0] is text:
        closing = cached[1].get(tick_start)
    else:
        found = text.find(fence, tick_end)
        closing = found if found != -1 else None
        if closing is None and state is not None:
            runs = [(run.start(), run.end() - run.start()) for run in BACKTICK_RUN_RE.finditer(text)]
            next_runs: dict[int, int | None] = {}
            stack: list[tuple[int, int]] = []
            for position, length in reversed(runs):
                while stack and stack[-1][1] < length:
                    stack.pop()
                next_runs[position] = stack[-1][0] if stack else None
                stack.append((position, length))
            state.store.get(ROLE_RUNS)[id(text)] = (text, next_runs)
    if closing is None:
        return None

    return name, text[tick_end:closing], closing + len(fence), tick_end, closing


nodes: dict[str, type[Node]] = {}


def setup(wen: Wenmode, /) -> None:
    wen.register_rule(RoleRule)
