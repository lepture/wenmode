from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Blockquote as BlockquoteNode
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
    def __init__(self) -> None:
        super().__init__('blockquote', r'[ \t]{0,3}>')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> BlockquoteNode:
        if state.depth >= parser.max_container_depth - 1:
            return BlockquoteNode(children=parse_shallow_block(parser, BLOCKQUOTE_RE, state))

        lines: list[str] = []
        paragraph_open = False
        lazy_used = False
        while not state.done:
            line = state.line
            quote = BLOCKQUOTE_RE.match(line)
            if quote is None:
                if paragraph_open and line.strip() != '' and not parser.is_paragraph_interrupt(line, state):
                    lines.append(('    ' if lazy_used and is_setext_marker(line) else '') + line)
                    lazy_used = True
                    state.advance()
                    continue
                break
            line_end = '\n' if line.endswith('\n') else ''
            content = expand_leading_tabs(quote.group(1), 2)
            lines.append(content + line_end)
            paragraph_open = content.strip() != '' and (
                not starts_nonparagraph_block(parser, content) or has_nested_blockquote(content)
            )
            lazy_used = False
            state.advance()

        return BlockquoteNode(children=parser.parse_blocks(''.join(lines), parent_state=state))


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
