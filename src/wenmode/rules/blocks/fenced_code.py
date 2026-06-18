from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Code, Node, Paragraph
from wenmode.state import BlockState
from wenmode.utils import normalize_label_text

from ..base import BlockRule
from .util import collect_until

if TYPE_CHECKING:
    from wenmode.parser import Parser


FENCE_OPENER_RE = re.compile(r'(?P<indent>[ \t]{0,3})(`{3,}|~{3,})(.*)$')


class FencedCode(BlockRule):
    """Parse fenced code blocks opened by backticks or tildes.

    Markdown syntax:

    .. code-block:: markdown

       ```python
       print(1)
       ```
    """

    def __init__(self) -> None:
        super().__init__('fenced_code', r'[ \t]{0,3}(?:`{3,}|~{3,})')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node:
        opener = FENCE_OPENER_RE.match(state.line.rstrip('\r\n'))
        if opener is None:
            state.advance()
            return Code(value='')

        indent = len(opener.group('indent').replace('\t', '    '))
        fence = opener.group(2)
        fence_char = fence[0]
        info = opener.group(3).strip()
        if fence_char == '`' and '`' in info:
            paragraph_lines: list[str] = []
            while not state.done and state.line.strip() != '':
                paragraph_lines.append(state.line)
                state.advance()
            return Paragraph(children=parser.parse_inlines(''.join(paragraph_lines).strip(), state))
        info = normalize_label_text(info)
        info_parts = info.split(None, 1)
        lang = info_parts[0] if info_parts else None
        meta = info_parts[1] if len(info_parts) > 1 else None
        state.advance()

        closer = re.compile(rf'[ \t]{{0,3}}{re.escape(fence_char)}{{{len(fence)},}}[ \t]*$')
        lines = collect_until(
            state,
            lambda line: closer.match(line.rstrip('\r\n')) is not None,
            lambda line: strip_fence_indent(line, indent),
        )

        return Code(value=''.join(lines), lang=lang, meta=meta)


def strip_fence_indent(line: str, indent: int) -> str:
    removed = 0
    index = 0
    while removed < indent and index < len(line) and line[index] == ' ':
        removed += 1
        index += 1
    return line[index:]
