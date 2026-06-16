from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import InlineCode as InlineCodeNode
from wenmode.nodes import Node
from wenmode.rules.base import InlineRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


class InlineCode(InlineRule):
    def __init__(self) -> None:
        super().__init__('inline_code', r'`+')

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        if match.start() > 0 and text[match.start() - 1] == '`':
            return None, match.start()
        marker = match.group(0)
        closer = re.search(rf'(?<!`){re.escape(marker)}(?!`)', text[match.end() :])
        if closer is None:
            return None, match.start()
        end = match.end() + closer.start()
        value = re.sub(r'\r\n?|\n', ' ', text[match.end() : end])
        if len(value) >= 2 and value.startswith(' ') and value.endswith(' ') and any(char != ' ' for char in value):
            value = value[1:-1]
        return InlineCodeNode(value=value), end + len(marker)
