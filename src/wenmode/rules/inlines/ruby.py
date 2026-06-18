from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Link as LinkNode
from wenmode.nodes import Node
from wenmode.nodes import Ruby as RubyNode
from wenmode.state import BlockState
from wenmode.utils import normalize_label

from ..base import InlineRule
from ..references import REFERENCES_KEY
from .link import closing_bracket_cache, find_closing_bracket, invalid_reference_label, parse_direct_destination

if TYPE_CHECKING:
    from wenmode.parser import Parser


RUBY_PATTERN = r'\[(?:\w+\([\w ]+\))+\]'
RUBY_SEGMENT_RE = re.compile(r'(\w+)\(([\w ]+)\)')


class Ruby(InlineRule):
    """Parse ruby annotation syntax.

    Markdown syntax:

    .. code-block:: markdown

       [漢字(kanji)]
    """

    order = 90

    def __init__(self) -> None:
        super().__init__('ruby', RUBY_PATTERN, '[')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        ruby = RubyNode(segments=parse_ruby_segments(match.group(0)))
        end = match.end()
        link = parse_ruby_link(parser, text, end, ruby, state)
        if link is not None:
            return link
        return ruby, end


def parse_ruby_segments(value: str) -> list[dict[str, str]]:
    return [{'base': match.group(1), 'text': match.group(2)} for match in RUBY_SEGMENT_RE.finditer(value[1:-1])]


def parse_ruby_link(
    parser: Parser, text: str, start: int, ruby: RubyNode, state: BlockState | None
) -> tuple[Node, int] | None:
    if 'link' not in parser.rules or start >= len(text):
        return None

    if text[start] == '(':
        direct = parse_direct_destination(text, start)
        if direct is None:
            return None
        url, title, end = direct
        return LinkNode(url=url, title=title, children=[ruby]), end

    if text[start] != '[':
        return None

    ref_end = find_closing_bracket(text, start + 1, closing_bracket_cache(state))
    if ref_end is None:
        return None

    label = text[start + 1 : ref_end]
    if not label or invalid_reference_label(label):
        return None

    reference = state.store.get(REFERENCES_KEY).get(normalize_label(label)) if state is not None else None
    if reference is None:
        return None

    return LinkNode(url=reference.url, title=reference.title, children=[ruby]), ref_end + 1
