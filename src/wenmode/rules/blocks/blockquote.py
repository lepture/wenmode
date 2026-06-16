from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Blockquote as BlockquoteNode
from wenmode.nodes import Node, Paragraph
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState
from wenmode.utils import expand_leading_tabs

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


class Blockquote(BlockRule):
    def __init__(self) -> None:
        super().__init__('blockquote', r'[ \t]{0,3}>')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> BlockquoteNode:
        if state.depth >= parser.max_container_depth - 1:
            return parse_shallow_blockquote(parser, state)

        lines: list[str] = []
        paragraph_open = False
        lazy_used = False
        while not state.done:
            line = state.line
            quote = re.match(r'[ \t]{0,3}> ?(.*)', line)
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


def parse_shallow_blockquote(parser: Wenmode, state: BlockState) -> BlockquoteNode:
    lines: list[str] = []
    while not state.done:
        quote = re.match(r'[ \t]{0,3}> ?(.*)', state.line)
        if quote is None:
            break
        lines.append(quote.group(1).strip())
        state.advance()
    text = '\n'.join(line for line in lines if line).strip()
    children: list[Node] = [Paragraph(children=parser.parse_inlines(text, state))] if text else []
    return BlockquoteNode(children=children)


def has_nested_blockquote(line: str) -> bool:
    return re.match(r'[ \t]{0,3}(?:[*+-]|\d{1,9}[.)])[ \t]+>', line) is not None


def starts_nonparagraph_block(parser: Wenmode, line: str) -> bool:
    rule_names = {'atx_heading', 'fenced_code', 'list', 'indented_code', 'thematic_break'}
    for name in rule_names:
        rule = parser.rules.get(name)
        if isinstance(rule, BlockRule) and re.match(rule.pattern, line):
            return True
    return False


def is_setext_marker(line: str) -> bool:
    return re.match(r'[ \t]{0,3}(=+|-+)[ \t]*$', line) is not None
