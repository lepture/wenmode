from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import Node, Parent, Position, Text
from wenmode.renderers import render_node_children
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer
from wenmode.rules.base import BlockRule, Rule
from wenmode.rules.transforms import RootTransform

from .._parser.state import BlockState
from .._parser.store import StateKey
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.nodes import Root
    from wenmode.parser import Parser

AbbreviationStart = tuple[str, str]

ABBREVIATION_START_RE = re.compile(r'^[ \t]{0,3}\*\[(?P<label>[^\]\n]+)\]:[ \t]*')
ABBREVIATION_CONTINUATION_RE = re.compile(r'^(?: {3,}|\t)')


@dataclass
class AbbreviationState:
    label: str
    title: str


@dataclass
class AbbreviationNode(Parent):
    """Abbreviation node."""

    title: str = ''
    type: str = 'abbreviation'


def create_abbreviations() -> dict[str, AbbreviationState]:
    return {}


ABBREVIATIONS_KEY = StateKey('wenmode.abbreviations', create_abbreviations)


class AbbreviationRule(Rule):
    """Parse abbreviation definitions and rewrite matching text nodes."""

    name = 'abbreviation'

    def __init__(self) -> None:
        super().__init__()
        self.root_transforms = [AbbreviationTransform()]


class AbbreviationDefinitionRule(BlockRule):
    order: ClassVar[int] = 80
    name = 'abbreviation_definition'
    pattern = r'[ \t]{0,3}\*\['

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> None:
        parsed = parse_abbreviation_definition(state, state.index)
        if parsed is None:
            return None

        next_index, label, title = parsed
        state.store.get(ABBREVIATIONS_KEY)[label] = AbbreviationState(label=label, title=title)
        state.index = next_index
        return None


class AbbreviationTransform(RootTransform):
    name = 'abbreviation'
    defer_inlines = True
    required_rules: Sequence[type[Rule] | Rule] = [AbbreviationDefinitionRule]

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        abbreviations = state.store.get(ABBREVIATIONS_KEY)
        if not abbreviations:
            return
        pattern = re.compile('|'.join(re.escape(label) for label in sorted(abbreviations, key=len, reverse=True)))
        transform_abbreviations(root, abbreviations, pattern)


def parse_abbreviation_definition(state: BlockState, index: int) -> tuple[int, str, str] | None:
    parsed = parse_abbreviation_start(state.line_at(index))
    if parsed is None:
        return None

    label, title = parsed
    title_lines = [title]
    index += 1
    if title_lines[0] == '':
        while state.has_index(index):
            continuation = parse_abbreviation_continuation(state.line_at(index))
            if continuation is None:
                break
            title_lines.append(continuation)
            index += 1

    return index, label, '\n'.join(title_lines).strip()


def parse_abbreviation_start(line: str) -> AbbreviationStart | None:
    text = line.rstrip('\r\n')
    match = ABBREVIATION_START_RE.match(text)
    if match is None:
        return None
    return match.group('label'), text[match.end() :]


def parse_abbreviation_continuation(line: str) -> str | None:
    text = line.rstrip('\r\n')
    match = ABBREVIATION_CONTINUATION_RE.match(text)
    if match is None:
        return None
    return text[match.end() :]


def transform_abbreviations(node: Parent, definitions: dict[str, AbbreviationState], pattern: re.Pattern[str]) -> None:
    children: list[Node] = []
    changed = False
    for child in node.children:
        if isinstance(child, Text):
            replaced = replace_abbreviations(child, definitions, pattern)
            children.extend(replaced)
            changed = changed or replaced != [child]
        else:
            if isinstance(child, Parent):
                transform_abbreviations(child, definitions, pattern)
            children.append(child)
    if changed:
        node.children = children


def replace_abbreviations(
    node: Text, definitions: dict[str, AbbreviationState], pattern: re.Pattern[str]
) -> list[Node]:
    nodes: list[Node] = []
    pos = 0
    for match in pattern.finditer(node.value):
        if match.start() > pos:
            nodes.append(
                Text(
                    value=node.value[pos : match.start()],
                    _parse_emphasis=node._parse_emphasis,
                    position=text_position(node, pos, match.start()),
                )
            )
        label = match.group(0)
        definition = definitions.get(label)
        if definition is None:
            nodes.append(
                Text(
                    value=label,
                    _parse_emphasis=node._parse_emphasis,
                    position=text_position(node, match.start(), match.end()),
                )
            )
        else:
            position = text_position(node, match.start(), match.end())
            nodes.append(
                AbbreviationNode(
                    title=definition.title,
                    position=position,
                    children=[Text(value=label, _parse_emphasis=False, position=position)],
                )
            )
        pos = match.end()
    if not nodes:
        return [node]
    if pos < len(node.value):
        nodes.append(
            Text(
                value=node.value[pos:],
                _parse_emphasis=node._parse_emphasis,
                position=text_position(node, pos, len(node.value)),
            )
        )
    return nodes


def text_position(node: Text, start: int, end: int) -> Position | None:
    if node.position is None:
        return None
    return Position(start=node.position.start + start, end=node.position.start + end)


def render_html(renderer: HTMLRenderer, node: AbbreviationNode, context: HTMLRenderContext) -> str:
    if node.title:
        attrs = {'title': node.title}
    else:
        attrs = {}
    return f'<abbr{renderer.render_attrs(attrs)}>{renderer.render_children(node.children, context)}</abbr>'


def render_rst(renderer: RSTRenderer, node: AbbreviationNode, context: RSTRenderContext) -> str:
    content = renderer.render_children(node.children, context)
    if not node.title:
        return content
    return f':abbr:`{content} ({renderer.escape_text(node.title)})`'


nodes = [AbbreviationNode]
rules: list[type[Rule] | Rule] = [AbbreviationRule]
handlers: RendererHandlers = {
    'html': {AbbreviationNode.type: render_html},
    'markdown': {AbbreviationNode.type: render_node_children},
    'rst': {AbbreviationNode.type: render_rst},
    'asciidoc': {AbbreviationNode.type: render_node_children},
}


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
