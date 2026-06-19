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
        super().__init__('inline_spoiler', r'>!', '>')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        parsed = parse_spoiler_span(text, match.start())
        if parsed is None:
            return None, match.start()

        spoiler_text, content_start, content_end, end = parsed
        return (
            InlineSpoilerNode(
                children=parser.parse_inlines(
                    spoiler_text,
                    state,
                    source=parser.inline_source(text, content_start, content_end),
                )
            ),
            end,
        )


def parse_spoiler_span(text: str, start: int) -> tuple[str, int, int, int] | None:
    content_start = start + 2
    close = text.find('!<', content_start)
    while close != -1:
        trimmed = trim_spoiler_text(text[content_start:close])
        if trimmed is not None:
            spoiler_text, trim_start, trim_end = trimmed
            return spoiler_text, content_start + trim_start, content_start + trim_end, close + 2
        close = text.find('!<', close + 2)
    return None


def trim_spoiler_text(text: str) -> tuple[str, int, int] | None:
    start = 0
    while start < len(text) and text[start].isspace():
        start += 1

    end = len(text)
    while end > start and text[end - 1].isspace():
        end -= 1

    if end > start:
        value = text[start:end]
        return None if '\n' in value else (value, start, end)

    for index, char in reversed(list(enumerate(text))):
        if char != '\n':
            return char, index, index + 1
    return None
