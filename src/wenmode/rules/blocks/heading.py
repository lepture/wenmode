from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Heading, Node

from ..._parser.state import BlockState
from ..base import BlockRule, ContinueRule
from ..transforms import NodeTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser


SETEXT_HEADING_RE = re.compile(r' {0,3}(=+|-+)[ \t]*$')


class AtxHeading(BlockRule):
    """Parse hash-prefixed ATX headings.

    Markdown syntax:

    .. code-block:: markdown

       # Heading

    :param transforms: Node transforms to run after parsing the heading.
    """

    name = 'atx_heading'
    pattern = r' {0,3}#{1,6}(?:[ \t]+|$)'

    def __init__(self, transforms: Iterable[NodeTransform] = ()) -> None:
        super().__init__()
        self.node_transforms = list(transforms)

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Heading:
        line = state.line.rstrip('\r\n')
        parsed = cast(tuple[str, str, int], parse_atx_heading_line(line))
        marker, content, content_start = parsed
        if content.strip('#').strip() == '':
            content = ''
        state.advance()
        text = content.strip()
        leading = len(content) - len(content.lstrip())
        source = state.source.line_text(state.index - 1, content_start + leading, text)
        return Heading(depth=len(marker), children=parser.parse_inlines(text, state, source=source))


class SetextHeading(ContinueRule):
    """Parse setext headings from paragraph continuations.

    Markdown syntax:

    .. code-block:: markdown

       Heading
       ---

    :param transforms: Node transforms to run after parsing the heading.
    """

    name = 'setext_heading'

    def __init__(self, transforms: Iterable[NodeTransform] = ()) -> None:
        super().__init__()
        self.node_transforms = list(transforms)

    def matches(self, line: str) -> bool:
        stripped = line.lstrip(' ')
        return stripped.startswith(('=', '-'))

    def parse_paragraph_continuation(self, parser: Parser, state: BlockState, lines: list[str]) -> Node | None:
        marker = SETEXT_HEADING_RE.match(state.line)
        if marker is None:
            return None

        start_index = state.index - len(lines)
        state.advance()
        if marker.group(1).startswith('='):
            depth = 1
        else:
            depth = 2
        text = ''.join(lines).strip()
        return Heading(
            depth=depth, children=parser.parse_inlines(text, state, source=state.source.paragraph(lines, start_index))
        )


def parse_atx_heading_line(line: str) -> tuple[str, str, int] | None:
    index = 0
    while index < len(line) and index < 3 and line[index] == ' ':
        index += 1

    marker_start = index
    while index < len(line) and line[index] == '#' and index - marker_start < 6:
        index += 1
    if index == marker_start:
        return None
    if index < len(line) and line[index] not in {' ', '\t'}:
        return None

    marker = line[marker_start:index]
    while index < len(line) and line[index] in {' ', '\t'}:
        index += 1
    return marker, strip_atx_closing_sequence(line[index:]), index


def strip_atx_closing_sequence(content: str) -> str:
    end = len(content)
    while end > 0 and content[end - 1] in {' ', '\t'}:
        end -= 1

    marker_start = end
    while marker_start > 0 and content[marker_start - 1] == '#':
        marker_start -= 1
    if marker_start == end or marker_start == 0 or content[marker_start - 1] not in {' ', '\t'}:
        return content

    content_end = marker_start - 1
    while content_end > 0 and content[content_end - 1] in {' ', '\t'}:
        content_end -= 1
    return content[:content_end]
