from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from wenmode.headings import Slugger, add_heading_ids
from wenmode.nodes import Heading, Node
from wenmode.state import BlockState

from ..base import BlockRule, ContinueRule, Rule
from ..transforms import RootTransform

if TYPE_CHECKING:
    from wenmode.nodes import Root
    from wenmode.parser import Parser


SETEXT_HEADING_RE = re.compile(r'[ \t]{0,3}(=+|-+)[ \t]*$')


class HeadingIdTransform:
    """Root transform that adds generated IDs to heading nodes.

    :param slugger_factory: Slugger class used to generate heading IDs.
    """

    defer_inlines = False
    required_rules: Sequence[type[Rule] | Rule] = ()

    def __init__(self, slugger_factory: type[Slugger] = Slugger) -> None:
        self.slugger_factory = slugger_factory
        self.name = f'heading_id:{slugger_factory.name}'

    def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
        pass

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        add_heading_ids(root, slugger=self.slugger_factory())


HeadingIdTransformOption = bool | HeadingIdTransform


def resolve_heading_id_transform(option: HeadingIdTransformOption) -> list[RootTransform]:
    if option is False:
        return []
    if option is True:
        return [HeadingIdTransform()]
    return [option]


class AtxHeading(BlockRule):
    """Parse hash-prefixed ATX headings.

    Markdown syntax:

    .. code-block:: markdown

       # Heading

    :param id_transform: ``True`` or a custom transform to generate heading IDs.
    """

    def __init__(self, id_transform: HeadingIdTransformOption = False) -> None:
        super().__init__('atx_heading', r'[ \t]{0,3}#{1,6}(?:[ \t]+|$)')
        self.root_transforms = resolve_heading_id_transform(id_transform)

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Heading:
        line = state.line.rstrip('\r\n')
        parsed = parse_atx_heading_line(line)
        if parsed is None:
            state.advance()
            return Heading(children=[])

        marker, content = parsed
        if content.strip('#').strip() == '':
            content = ''
        state.advance()
        return Heading(depth=len(marker), children=parser.parse_inlines(content.strip(), state))


class SetextHeading(ContinueRule):
    """Parse setext headings from paragraph continuations.

    Markdown syntax:

    .. code-block:: markdown

       Heading
       ---

    :param id_transform: ``True`` or a custom transform to generate heading IDs.
    """

    def __init__(self, id_transform: HeadingIdTransformOption = False) -> None:
        super().__init__('setext_heading')
        self.root_transforms = resolve_heading_id_transform(id_transform)

    def matches(self, line: str) -> bool:
        stripped = line.lstrip(' \t')
        return stripped.startswith(('=', '-'))

    def parse_paragraph_continuation(self, parser: Parser, state: BlockState, lines: list[str]) -> Node | None:
        marker = SETEXT_HEADING_RE.match(state.line)
        if marker is None:
            return None

        state.advance()
        depth = 1 if marker.group(1).startswith('=') else 2
        text = ''.join(lines).strip()
        return Heading(depth=depth, children=parser.parse_inlines(text, state))


def parse_atx_heading_line(line: str) -> tuple[str, str] | None:
    index = 0
    while index < len(line) and index < 3 and line[index] in {' ', '\t'}:
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
    return marker, strip_atx_closing_sequence(line[index:])


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
