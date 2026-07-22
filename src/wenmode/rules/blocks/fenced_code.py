from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Code, Node, Paragraph
from wenmode.utils import normalize_label_text

from ..._parser.state import BlockState
from ..base import BlockCandidate, BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


FENCE_OPENER_RE = re.compile(r'(?P<indent> {0,3})(?P<fence>`{3,}|~{3,})')


class FencedCode(BlockRule):
    """Parse fenced code blocks opened by backticks or tildes.

    Markdown syntax:

    .. code-block:: markdown

       ```python
       print(1)
       ```
    """

    name = 'fenced_code'
    pattern = r' {0,3}(?:`{3,}|~{3,})'

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Node:
        opener = cast(re.Match[str], FENCE_OPENER_RE.match(state.line.rstrip('\r\n')))
        indent = len(opener.group('indent').replace('\t', '    '))
        fence = opener.group('fence')
        fence_char = fence[0]
        info = opener.string[opener.end() :].strip()
        if fence_char == '`' and '`' in info:
            paragraph_lines: list[str] = []
            while not state.done and state.line.strip() != '':
                paragraph_lines.append(state.line)
                state.advance()
            return Paragraph(children=parser.parse_inlines(''.join(paragraph_lines).strip(), state))
        info = normalize_label_text(info)
        info_parts = info.split(None, 1)
        if info_parts:
            lang = info_parts[0]
        else:
            lang = None
        if len(info_parts) > 1:
            meta = info_parts[1]
        else:
            meta = None
        state.advance()

        closer = re.compile(rf' {{0,3}}{re.escape(fence_char)}{{{len(fence)},}}[ \t]*$')
        lines = state.consume_until(
            lambda line: closer.match(line.rstrip('\r\n')) is not None, lambda line: strip_fence_indent(line, indent)
        )

        return Code(value=''.join(lines), lang=lang, meta=meta)


def strip_fence_indent(line: str, indent: int) -> str:
    removed = 0
    index = 0
    while removed < indent and index < len(line) and line[index] == ' ':
        removed += 1
        index += 1
    return line[index:]
