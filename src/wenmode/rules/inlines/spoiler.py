from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import InlineSpoiler as InlineSpoilerNode
from wenmode.nodes import Node
from wenmode.state import BlockState

from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


class InlineSpoiler(InlineRule):
    """Parse spoiler spans delimited by ``>!`` and ``!<``.

    Markdown syntax:

    .. code-block:: markdown

       >! secret !<
    """

    def __init__(self) -> None:
        super().__init__('inline_spoiler', r'>!\s*(?P<spoiler_text>.+?)\s*!<', '>')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return InlineSpoilerNode(children=parser.parse_inlines(match.group('spoiler_text'), state)), match.end()
