from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING

from wenmode.nodes import Node, Paragraph
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


def collect_until(
    state: BlockState, is_closer: Callable[[str], bool], transform: Callable[[str], str] | None = None
) -> list[str]:
    lines: list[str] = []
    while not state.done:
        line = state.line
        if is_closer(line):
            state.advance()
            break
        if transform is not None:
            lines.append(transform(line))
        else:
            lines.append(line)
        state.advance()
    return lines


def parse_shallow_block(parser: Parser, regex: re.Pattern[str], state: BlockState) -> list[Node]:
    lines: list[str] = []
    while not state.done:
        quote = regex.match(state.line)
        if quote is None:
            break
        lines.append(quote.group(1).strip())
        state.advance()
    text = '\n'.join(line for line in lines if line).strip()
    if text:
        children: list[Node] = [Paragraph(children=parser.parse_inlines(text, state))]
    else:
        children = []
    return children
