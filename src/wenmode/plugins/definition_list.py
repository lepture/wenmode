from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import Node, Paragraph, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules import ContinueCandidate, ContinueRule, Rule

from .._parser.source import SourceCollector
from .._parser.state import BlockState
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

ParsedLine = tuple[int, str]

DESCRIPTION_RE = re.compile(r'^[ \t]{0,3}:[ \t]+')
INDENTED_RE = re.compile(r'^(?: {4}|\t)')


@dataclass
class DefinitionListNode(Parent):
    """Definition list node."""

    block: ClassVar[bool] = True
    type: str = 'definitionList'


@dataclass
class DefinitionTermNode(Parent):
    """Definition term node."""

    block: ClassVar[bool] = True
    type: str = 'definitionTerm'


@dataclass
class DefinitionDescriptionNode(Parent):
    """Definition description node."""

    spread: bool = False
    block: ClassVar[bool] = True
    type: str = 'definitionDescription'


class DefinitionListRule(ContinueRule):
    """Parse colon-prefixed definition list continuations."""

    name = 'definition_list'

    def match_candidate(self, line: str) -> ContinueCandidate | None:
        match = DESCRIPTION_RE.match(line)
        if match is None:
            return None
        return ContinueCandidate(line, match)

    def parse_paragraph_continuation(
        self, parser: Parser, state: BlockState, lines: list[str], candidate: ContinueCandidate
    ) -> DefinitionListNode | None:
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
        parsed = parse_description_line(state.line)
        if parsed is None:
            break
        text_start, parsed_text = parsed
        start_index = state.index
        text = parsed_text + line_ending(state.line)
        lines = [text]
        source = state.source.collect()
        source.add(state.index, text_start, text)
        state.advance()
        spread = collect_description_continuation(state, lines, source)
        children = parser.parse_blocks(''.join(lines), parent_state=state, source=source.map())
        description = DefinitionDescriptionNode(children=children, spread=spread)
        description.position = state.source.position_between(start_index, state.index)
        descriptions.append(description)
    return descriptions


def collect_description_continuation(state: BlockState, lines: list[str], source: SourceCollector) -> bool:
    spread = False
    while not state.done:
        if state.line.strip() == '':
            if not state.has(1) or parse_indented_line(state.peek(1)) is None:
                break
            spread = True
            lines.append(state.line)
            source.add(state.index, 0, state.line)
            state.advance()
            continue
        indented = parse_indented_line(state.line)
        if indented is None:
            break
        text_start, parsed_text = indented
        text = parsed_text + line_ending(state.line)
        lines.append(text)
        source.add(state.index, text_start, text)
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
        if parse_description_line(line) is not None:
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


def line_without_lf(line: str) -> str:
    if line.endswith('\n'):
        return line[:-1]
    return line


def parse_description_line(line: str) -> ParsedLine | None:
    text = line_without_lf(line)
    match = DESCRIPTION_RE.match(text)
    if match is None:
        return None
    return match.end(), text[match.end() :]


def parse_indented_line(line: str) -> ParsedLine | None:
    text = line_without_lf(line)
    match = INDENTED_RE.match(text)
    if match is None:
        return None
    return match.end(), text[match.end() :]


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


def render_asciidoc_list(renderer: AsciiDocRenderer, node: DefinitionListNode, context: AsciiDocRenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n'


def render_asciidoc_term(renderer: AsciiDocRenderer, node: DefinitionTermNode, context: AsciiDocRenderContext) -> str:
    return renderer.render_children(node.children, context).strip()


def render_asciidoc_description(
    renderer: AsciiDocRenderer, node: DefinitionDescriptionNode, context: AsciiDocRenderContext
) -> str:
    if not node.children:
        return '::\n'
    if not node.spread and len(node.children) == 1 and isinstance(node.children[0], Paragraph):
        return ':: ' + renderer.render_children(node.children[0].children, context).strip() + '\n'
    body = render_asciidoc_definition_body(renderer, node.children, context)
    if body:
        return '::\n+\n' + body + '\n'
    return '::\n'


def render_asciidoc_definition_body(
    renderer: AsciiDocRenderer, children: list[Node], context: AsciiDocRenderContext
) -> str:
    if not children:
        return ''
    if len(children) == 1 and isinstance(children[0], Paragraph):
        return renderer.render_children(children[0].children, context).strip()
    return renderer.render_children(children, context).rstrip('\n')


nodes = [DefinitionListNode, DefinitionTermNode, DefinitionDescriptionNode]
rules: list[type[Rule] | Rule] = [DefinitionListRule]
handlers: RendererHandlers = {
    'html': {
        DefinitionListNode.type: render_html_list,
        DefinitionTermNode.type: render_html_term,
        DefinitionDescriptionNode.type: render_html_description,
    },
    'markdown': {
        DefinitionListNode.type: render_markdown_list,
        DefinitionTermNode.type: render_markdown_term,
        DefinitionDescriptionNode.type: render_markdown_description,
    },
    'rst': {
        DefinitionListNode.type: render_rst_list,
        DefinitionTermNode.type: render_rst_term,
        DefinitionDescriptionNode.type: render_rst_description,
    },
    'asciidoc': {
        DefinitionListNode.type: render_asciidoc_list,
        DefinitionTermNode.type: render_asciidoc_term,
        DefinitionDescriptionNode.type: render_asciidoc_description,
    },
}


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
