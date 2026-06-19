from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Blockquote as BlockquoteNode
from wenmode.nodes import Point
from wenmode.state import BlockState
from wenmode.utils import expand_leading_tabs

from ..base import BlockRule
from .util import parse_shallow_block

if TYPE_CHECKING:
    from wenmode.parser import Parser


BLOCKQUOTE_RE = re.compile(r'[ \t]{0,3}> ?(.*)')
NESTED_BLOCKQUOTE_RE = re.compile(r'[ \t]{0,3}(?:[*+-]|\d{1,9}[.)])[ \t]+>')
SETEXT_MARKER_RE = re.compile(r'[ \t]{0,3}(=+|-+)[ \t]*$')


class Blockquote(BlockRule):
    """Parse ``>`` block quote containers.

    Markdown syntax:

    .. code-block:: markdown

       > blockquote
    """

    def __init__(self) -> None:
        super().__init__('blockquote', r'[ \t]{0,3}>')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> BlockquoteNode:
        if state.depth >= parser.max_container_depth - 1:
            return BlockquoteNode(children=parse_shallow_block(parser, BLOCKQUOTE_RE, state))

        lines: list[str] = []
        source_parts: list[tuple[str, Point]] = []
        paragraph_open = False
        lazy_used = False
        while not state.done:
            line = state.line
            quote = BLOCKQUOTE_RE.match(line)
            if quote is None:
                if paragraph_open and line.strip() != '' and not parser.is_paragraph_interrupt(line, state):
                    text = ('    ' if lazy_used and is_setext_marker(line) else '') + line
                    lines.append(text)
                    point = state.point_at_line_offset(state.index, 0)
                    if point is not None:
                        source_parts.append((text, point))
                    lazy_used = True
                    state.advance()
                    continue
                break
            line_end = '\n' if line.endswith('\n') else ''
            content = expand_leading_tabs(quote.group(1), 2)
            text = content + line_end
            lines.append(text)
            point = state.point_at_line_offset(state.index, quote.start(1))
            if point is not None:
                source_parts.append((text, point))
            paragraph_open = content.strip() != '' and (
                not starts_nonparagraph_block(parser, content) or has_nested_blockquote(content)
            )
            lazy_used = False
            state.advance()

        text = ''.join(lines)
        return BlockquoteNode(
            children=parser.parse_blocks(text, parent_state=state, source=parser.source_map_from_parts(source_parts))
        )


def has_nested_blockquote(line: str) -> bool:
    return NESTED_BLOCKQUOTE_RE.match(line) is not None


def starts_nonparagraph_block(parser: Parser, line: str) -> bool:
    rule_names = {
        'atx_heading',
        'container_directive',
        'fenced_code',
        'fenced_directive',
        'indented_code',
        'leaf_directive',
        'list',
        'thematic_break',
    }
    for name in rule_names:
        rule = parser.rules.get(name)
        if isinstance(rule, BlockRule) and re.match(rule.pattern, line):
            return True
    return False


def is_setext_marker(line: str) -> bool:
    return SETEXT_MARKER_RE.match(line) is not None
