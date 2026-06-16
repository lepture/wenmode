from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Blockquote as BlockquoteNode
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


class Blockquote(BlockRule):
    def __init__(self) -> None:
        super().__init__('blockquote', r'[ \t]{0,3}>')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> BlockquoteNode:
        lines: list[str] = []
        paragraph_open = False
        lazy_used = False
        while not state.done:
            line = state.line
            quote = re.match(r'[ \t]{0,3}> ?(.*)', line)
            if quote is None:
                if paragraph_open and line.strip() != '' and not parser.is_paragraph_interrupt(line):
                    lines.append(('    ' if lazy_used and is_setext_marker(line) else '') + line)
                    lazy_used = True
                    state.advance()
                    continue
                break
            line_end = '\n' if line.endswith('\n') else ''
            content = expand_leading_tabs(quote.group(1), 2)
            lines.append(content + line_end)
            paragraph_open = content.strip() != '' and (
                not starts_nonparagraph_block(content) or has_nested_blockquote(content)
            )
            lazy_used = False
            state.advance()

        return BlockquoteNode(children=parser.parse_blocks(''.join(lines)))


def starts_nonparagraph_block(line: str) -> bool:
    return bool(
        re.match(r'[ \t]{0,3}(?:#{1,6}(?:[ \t]+|$)|(?:`{3,}|~{3,})|(?:[*+-]|\d{1,9}[.)])(?:[ \t]+|$))', line)
        or re.match(r'[ \t]{4,}', line)
        or re.match(r'[ \t]{0,3}(?:\*[ \t]*){3,}$', line)
        or re.match(r'[ \t]{0,3}(?:-[ \t]*){3,}$', line)
        or re.match(r'[ \t]{0,3}(?:_[ \t]*){3,}$', line)
    )


def has_nested_blockquote(line: str) -> bool:
    return re.match(r'[ \t]{0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]+)>', line) is not None


def is_setext_marker(line: str) -> bool:
    return re.match(r'[ \t]{0,3}(=+|-+)[ \t]*$', line) is not None


def expand_leading_tabs(line: str, start_column: int = 0) -> str:
    column = start_column
    parts: list[str] = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == ' ':
            parts.append(' ')
            column += 1
        elif char == '\t':
            size = 4 - column % 4
            parts.append(' ' * size)
            column += size
        else:
            break
        index += 1
    return ''.join(parts) + line[index:]
