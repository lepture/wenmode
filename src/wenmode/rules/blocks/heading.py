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


ATX_HEADING_RE = re.compile(r'[ \t]{0,3}(#{1,6})(?:[ \t]+|$)(.*?)(?:[ \t]+#+[ \t]*)?$')
SETEXT_HEADING_RE = re.compile(r'[ \t]{0,3}(=+|-+)[ \t]*$')


class HeadingIdTransform:
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
    def __init__(self, id_transform: HeadingIdTransformOption = False) -> None:
        super().__init__('atx_heading', r'[ \t]{0,3}#{1,6}(?:[ \t]+|$)')
        self.root_transforms = resolve_heading_id_transform(id_transform)

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Heading:
        line = state.line.rstrip('\r\n')
        heading = ATX_HEADING_RE.match(line)
        if heading is None:
            state.advance()
            return Heading(children=[])

        marker, content = heading.groups()
        if content.strip('#').strip() == '':
            content = ''
        state.advance()
        return Heading(depth=len(marker), children=parser.parse_inlines(content.strip(), state))


class SetextHeading(ContinueRule):
    def __init__(self, id_transform: HeadingIdTransformOption = False) -> None:
        super().__init__('setext_heading')
        self.root_transforms = resolve_heading_id_transform(id_transform)

    def parse_paragraph_continuation(
        self, parser: Parser, state: BlockState, lines: list[str]
    ) -> Node | None:
        marker = SETEXT_HEADING_RE.match(state.line)
        if marker is None:
            return None

        state.advance()
        depth = 1 if marker.group(1).startswith('=') else 2
        text = ''.join(lines).strip()
        return Heading(depth=depth, children=parser.parse_inlines(text, state))
