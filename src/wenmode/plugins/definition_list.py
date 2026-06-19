from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Node, Paragraph, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules.base import ContinueRule, Rule
from wenmode.state import BlockState, SourceCollector

from ..utils import match_pattern
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

DESCRIPTION_RE = re.compile(r'^[ \t]{0,3}:[ \t]+(?P<text>.*)$')
INDENTED_RE = re.compile(r'^(?: {4}|\t)(?P<text>.*)$')


@dataclass
class DefinitionListNode(Parent):
    """Definition list node."""

    type: str = 'definitionList'


@dataclass
class DefinitionTermNode(Parent):
    """Definition term node."""

    type: str = 'definitionTerm'


@dataclass
class DefinitionDescriptionNode(Parent):
    """Definition description node."""

    spread: bool = False
    type: str = 'definitionDescription'


class DefinitionListRule(ContinueRule):
    """Parse colon-prefixed definition list continuations."""

    def __init__(self) -> None:
        super().__init__('definition_list')

    def matches(self, line: str) -> bool:
        return line.lstrip(' \t').startswith(':')

    def parse_paragraph_continuation(
        self, parser: Parser, state: BlockState, lines: list[str]
    ) -> DefinitionListNode | None:
        if DESCRIPTION_RE.match(state.line) is None:
            return None

        term_start_index = state.index - len(lines)
        children: list[Node] = create_terms(parser, lines, state, term_start_index)
        children.extend(parse_descriptions(parser, state))
        parse_following_items(parser, state, children)
        return DefinitionListNode(children=children)


def create_terms(parser: Parser, lines: list[str], state: BlockState, start_index: int) -> list[Node]:
    terms: list[Node] = []
    for offset, line in enumerate(lines):
        if not line.strip():
            continue
        text = line.strip()
        leading = len(line) - len(line.lstrip())
        term = DefinitionTermNode(
            children=parser.parse_inlines(
                text, state, source=state.source.line_text(start_index + offset, leading, text)
            )
        )
        term.position = state.source.position_between(start_index + offset, start_index + offset + 1)
        terms.append(term)
    return terms


def parse_descriptions(parser: Parser, state: BlockState) -> list[DefinitionDescriptionNode]:
    descriptions: list[DefinitionDescriptionNode] = []
    while not state.done:
        match = DESCRIPTION_RE.match(state.line)
        if match is None:
            break
        start_index = state.index
        text = match.group('text') + line_ending(state.line)
        lines = [text]
        source = state.source.collect()
        source.add(state.index, match.start('text'), text)
        state.advance()
        spread = collect_description_continuation(state, lines, source)
        children = parser.parse_blocks(
            ''.join(lines),
            parent_state=state,
            source=source.map(),
        )
        description = DefinitionDescriptionNode(children=children, spread=spread)
        description.position = state.source.position_between(start_index, state.index)
        descriptions.append(description)
    return descriptions


def collect_description_continuation(state: BlockState, lines: list[str], source: SourceCollector) -> bool:
    spread = False
    while not state.done:
        if state.line.strip() == '':
            if not state.has(1) or INDENTED_RE.match(state.peek(1)) is None:
                break
            spread = True
            lines.append(state.line)
            source.add(state.index, 0, state.line)
            state.advance()
            continue
        indented = INDENTED_RE.match(state.line)
        if indented is None:
            break
        text = indented.group('text') + line_ending(state.line)
        lines.append(text)
        source.add(state.index, indented.start('text'), text)
        state.advance()
    return spread


def parse_following_items(parser: Parser, state: BlockState, children: list[Node]) -> None:
    while not state.done:
        parsed = parse_following_terms(state)
        if parsed is None:
            return
        terms, term_start_index, next_index = parsed
        state.index = next_index
        children.extend(create_terms(parser, terms, state, term_start_index))
        children.extend(parse_descriptions(parser, state))


def parse_following_terms(state: BlockState) -> tuple[list[str], int, int] | None:
    index = state.index
    while state.has_index(index) and state.line_at(index).strip() == '':
        index += 1
    start_index = index
    terms: list[str] = []
    while state.has_index(index):
        line = state.line_at(index)
        if line.strip() == '':
            return None
        if match_pattern(DESCRIPTION_RE, line):
            if terms:
                return terms, start_index, index
            return None
        if line.startswith((' ', '\t')):
            return None
        terms.append(line)
        index += 1
    return None


def line_ending(line: str) -> str:
    if line.endswith('\n'):
        return '\n'
    return ''


def render_html_list(renderer: HTMLRenderer, node: DefinitionListNode, context: HTMLRenderContext) -> str:
    return '<dl>\n' + renderer.render_children(node.children, context) + '</dl>\n'


def render_html_term(renderer: HTMLRenderer, node: DefinitionTermNode, context: HTMLRenderContext) -> str:
    return f'<dt>{renderer.render_children(node.children, context)}</dt>\n'


def render_html_description(renderer: HTMLRenderer, node: DefinitionDescriptionNode, context: HTMLRenderContext) -> str:
    if not node.spread and len(node.children) == 1 and isinstance(node.children[0], Paragraph):
        return f'<dd>{renderer.render_children(node.children[0].children, context)}</dd>\n'
    return '<dd>\n' + renderer.render_children(node.children, context) + '</dd>\n'


def render_markdown_list(renderer: MarkdownRenderer, node: DefinitionListNode, context: RenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n'


def render_markdown_term(renderer: MarkdownRenderer, node: DefinitionTermNode, context: RenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n'


def render_markdown_description(
    renderer: MarkdownRenderer, node: DefinitionDescriptionNode, context: RenderContext
) -> str:
    if not node.children:
        return ': \n'
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not node.spread and len(node.children) == 1 and isinstance(node.children[0], Paragraph):
        return ': ' + renderer.render_children(node.children[0].children, context) + '\n'
    lines = body.splitlines()
    return ': ' + lines[0] + '\n' + ''.join('    ' + line + '\n' for line in lines[1:])


def render_rst_list(renderer: RSTRenderer, node: DefinitionListNode, context: RSTRenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n'


def render_rst_term(renderer: RSTRenderer, node: DefinitionTermNode, context: RSTRenderContext) -> str:
    return renderer.render_children(node.children, context).strip() + '\n'


def render_rst_description(renderer: RSTRenderer, node: DefinitionDescriptionNode, context: RSTRenderContext) -> str:
    body = render_definition_body(renderer, node.children, context)
    if not body:
        return '  \n'
    return indent_block(body, '  ') + '\n'


def render_definition_body(renderer: RSTRenderer, children: list[Node], context: RSTRenderContext) -> str:
    if not children:
        return ''
    if len(children) == 1 and isinstance(children[0], Paragraph):
        return renderer.render_children(children[0].children, context)
    return renderer.render_children(children, context).rstrip('\n')


rules: list[type[Rule] | Rule] = [DefinitionListRule]
handlers: RendererHandlers = {
    'html': {
        'definitionList': render_html_list,
        'definitionTerm': render_html_term,
        'definitionDescription': render_html_description,
    },
    'markdown': {
        'definitionList': render_markdown_list,
        'definitionTerm': render_markdown_term,
        'definitionDescription': render_markdown_description,
    },
    'rst': {
        'definitionList': render_rst_list,
        'definitionTerm': render_rst_term,
        'definitionDescription': render_rst_description,
    },
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
