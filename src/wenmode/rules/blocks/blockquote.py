from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Blockquote as BlockquoteNode
from wenmode.utils import expand_leading_tabs

from ..._parser.state import BlockState
from ..base import BlockCandidate, BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser

    from ..._parser.source import SourceCollector


BLOCKQUOTE_RE = re.compile(r' {0,3}> ?')
NESTED_BLOCKQUOTE_RE = re.compile(r' {0,3}(?:[*+-]|\d{1,9}[.)])[ \t]+>')
SETEXT_MARKER_RE = re.compile(r' {0,3}(=+|-+)[ \t]*$')


class Blockquote(BlockRule):
    """Parse ``>`` block quote containers.

    Markdown syntax:

    .. code-block:: markdown

       > blockquote
    """

    name = 'blockquote'
    pattern = r' {0,3}>'

    @staticmethod
    def parse_text(parser: Parser, state: BlockState, source: SourceCollector) -> str:
        lines: list[str] = []
        paragraph_open = False
        lazy_used = False
        while not state.done:
            line = state.line
            quote = BLOCKQUOTE_RE.match(line)
            if quote is None:
                if paragraph_open and line.strip() != '' and not parser.is_paragraph_interrupt(line, state):
                    if lazy_used and SETEXT_MARKER_RE.match(line) is not None:
                        prefix = '    '
                    else:
                        prefix = ''
                    text = prefix + line
                    lines.append(text)
                    source.add(state.index, 0, text)
                    lazy_used = True
                    state.advance()
                    continue
                break
            content = expand_leading_tabs(line[quote.end() :], 2)
            text = content
            lines.append(text)
            source.add(state.index, quote.end(), text)
            paragraph_open = content.strip() != '' and (
                not starts_nonparagraph_block(parser, content) or NESTED_BLOCKQUOTE_RE.match(content) is not None
            )
            lazy_used = False
            state.advance()

        return ''.join(lines)

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> BlockquoteNode:
        source = state.source.collect()
        text = self.parse_text(parser, state, source)
        return BlockquoteNode(children=parser.parse_blocks(text, parent_state=state, source=source.map()))


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
        if isinstance(rule, BlockRule) and rule.compiled.match(line):
            return True
    return False
