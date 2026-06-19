from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import InlineCode as InlineCodeNode
from wenmode.nodes import Node
from wenmode.state import BlockState

from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


CODE_LINE_ENDING_RE = re.compile(r'\r\n?|\n')


class InlineCode(InlineRule):
    """Parse inline code spans.

    Markdown syntax:

    .. code-block:: markdown

       `code`
    """

    def __init__(self) -> None:
        super().__init__('inline_code', r'`+', '`')

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        if match.start() > 0 and text[match.start() - 1] == '`':
            return None, match.start()
        marker = match.group(0)
        closer = re.search(rf'(?<!`){re.escape(marker)}(?!`)', text[match.end() :])
        if closer is None:
            return None, match.start()
        end = match.end() + closer.start()
        value = CODE_LINE_ENDING_RE.sub(' ', text[match.end() : end])
        if len(value) >= 2 and value.startswith(' ') and value.endswith(' ') and any(char != ' ' for char in value):
            value = value[1:-1]
        return InlineCodeNode(value=value), end + len(marker)
