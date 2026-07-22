from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, TypeAlias

from wenmode.nodes import Node, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules import BlockCandidate, BlockRule, Rule
from wenmode.rules.blocks.html import HTML_SCRIPT_STYLE_RE, HtmlBlock
from wenmode.utils import compile_disallowed_html_filter, filter_disallowed_html, unquote_attribute_value

from .._parser.source import SourceCollector
from .._parser.state import BlockState
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


HtmlContainerAttributeValue: TypeAlias = str | bool

HTML_CONTAINER_OPENER_RE = re.compile(
    r'(?i)^[ \t]{0,3}<'
    r'(?P<name>[a-z][a-z0-9-]*)'
    r'(?P<attrs>(?:\s+[a-z_:][a-z0-9_.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*)'
    r'\s*>[ \t]*(?:\r?\n)?$'
)
HTML_ATTRIBUTE_RE = re.compile(
    r'(?i)\s+'
    r'(?P<name>[a-z_:][a-z0-9_.:-]*)'
    r'(?:\s*=\s*(?P<value>[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?'
)
VOID_TAGS = frozenset(
    {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
)


@dataclass
class HtmlContainerNode(Parent):
    """HTML block container whose body is parsed as Markdown blocks."""

    name: str = ''
    attributes: dict[str, HtmlContainerAttributeValue] | None = None
    opening: str = ''
    closing: str = ''
    block: ClassVar[bool] = True
    type: str = 'htmlContainer'


class HtmlContainer(BlockRule):
    """Parse standalone HTML tag pairs as containers with Markdown children.

    This rule is intended as a non-CommonMark replacement for ``HtmlBlock``.
    It uses the same ``html_block`` rule name so installing the plugin replaces
    the default rule instead of adding a second competing HTML block opener.
    """

    name = 'html_block'
    pattern = HtmlBlock.pattern

    def __init__(self, disallowed_tags: Sequence[str] = ()) -> None:
        super().__init__()
        self.disallowed_html_filter = compile_disallowed_html_filter(disallowed_tags)
        self.fallback = HtmlBlock(disallowed_tags=disallowed_tags)

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Node:
        if state.depth >= parser.max_container_depth - 1:
            return self.fallback.parse(parser, state, candidate)
        parsed = parse_html_container(parser, state, self.disallowed_html_filter)
        if parsed is not None:
            return parsed
        return self.fallback.parse(parser, state, candidate)


def parse_html_container(
    parser: Parser, state: BlockState, disallowed_html_filter: re.Pattern[str] | None
) -> HtmlContainerNode | None:
    opener = parse_container_opener(state.line)
    if opener is None:
        return None

    name, attributes, opening = opener
    if name in VOID_TAGS or HTML_SCRIPT_STYLE_RE.match(opening.lstrip(' \t')):
        return None

    close_index = find_matching_close_index(state, name)
    if close_index is None:
        return None

    source = state.source.collect()
    body = collect_container_body(state, source, close_index)
    closing = state.line.rstrip('\r\n')
    state.advance()

    original_opening = opening
    original_closing = closing
    opening = filter_disallowed_html(original_opening, disallowed_html_filter)
    closing = filter_disallowed_html(original_closing, disallowed_html_filter)
    if opening != original_opening or closing != original_closing:
        data = {'escaped': True}
    else:
        data = None
    return HtmlContainerNode(
        name=name,
        attributes=attributes,
        opening=opening,
        closing=closing,
        children=parser.parse_blocks(body, parent_state=state, source=source.map()),
        data=data,
    )


def parse_container_opener(line: str) -> tuple[str, dict[str, HtmlContainerAttributeValue] | None, str] | None:
    opening = line.rstrip('\r\n')
    match = HTML_CONTAINER_OPENER_RE.match(line)
    if match is None:
        return None
    return match.group('name').lower(), parse_html_attributes(match.group('attrs')), opening


def parse_html_attributes(text: str) -> dict[str, HtmlContainerAttributeValue] | None:
    attributes: dict[str, HtmlContainerAttributeValue] = {}
    index = 0
    while index < len(text):
        match = HTML_ATTRIBUTE_RE.match(text, index)
        if match is None:  # pragma: no cover - opener regex validates attribute text first
            return None
        value = match.group('value')
        if value is None:
            attributes[match.group('name')] = True
        else:
            attributes[match.group('name')] = unquote_attribute_value(value)
        index = match.end()
    return attributes or None


def find_matching_close_index(state: BlockState, name: str) -> int | None:
    closer = container_closer_re(name)
    depth = 0
    index = state.index + 1
    while state.has_index(index):
        line = state.line_at(index)
        opener = parse_container_opener(line)
        if opener is not None and opener[0] == name:
            depth += 1
            index += 1
            continue
        if closer.match(line):
            if depth == 0:
                return index
            depth -= 1
        index += 1
    return None


def container_closer_re(name: str) -> re.Pattern[str]:
    return re.compile(rf'(?i)^[ \t]{{0,3}}</{re.escape(name)}\s*>[ \t]*(?:\r?\n)?$')


def is_container_closer(line: str, name: str) -> bool:
    return container_closer_re(name).match(line) is not None


def collect_container_body(state: BlockState, source: SourceCollector, close_index: int) -> str:
    lines: list[str] = []
    state.advance()
    while state.index < close_index:
        line = state.line
        lines.append(line)
        source.add(state.index, 0, line)
        state.advance()
    return ''.join(lines)


def render_html_container(renderer: HTMLRenderer, node: HtmlContainerNode, context: HTMLRenderContext) -> str:
    opening = render_html_boundary(renderer, node, node.opening)
    closing = render_html_boundary(renderer, node, node.closing)
    return opening + '\n' + renderer.render_children(node.children, context) + closing + '\n'


def render_html_boundary(renderer: HTMLRenderer, node: HtmlContainerNode, value: str) -> str:
    if node.data and node.data.get('escaped'):
        return value
    return renderer.escape(value)


def render_markdown_container(renderer: MarkdownRenderer, node: HtmlContainerNode, context: RenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if body:
        return f'{node.opening}\n{body}\n{node.closing}\n\n'
    return f'{node.opening}\n{node.closing}\n\n'


def render_rst_container(renderer: RSTRenderer, node: HtmlContainerNode, context: RSTRenderContext) -> str:
    opening = '.. raw:: html\n\n' + indent_block(node.opening, '   ') + '\n\n'
    closing = '.. raw:: html\n\n' + indent_block(node.closing, '   ') + '\n\n'
    return opening + renderer.render_children(node.children, context) + closing


def render_asciidoc_container(
    renderer: AsciiDocRenderer, node: HtmlContainerNode, context: AsciiDocRenderContext
) -> str:
    opening = '++++\n' + node.opening + '\n++++\n\n'
    closing = '++++\n' + node.closing + '\n++++\n\n'
    return opening + renderer.render_children(node.children, context) + closing


rules: list[type[Rule] | Rule] = [HtmlContainer]
nodes = [HtmlContainerNode]
handlers: RendererHandlers = {
    'html': {HtmlContainerNode.type: render_html_container},
    'markdown': {HtmlContainerNode.type: render_markdown_container},
    'rst': {HtmlContainerNode.type: render_rst_container},
    'asciidoc': {HtmlContainerNode.type: render_asciidoc_container},
}


@dataclass(frozen=True)
class HtmlContainerPlugin:
    disallowed_tags: Sequence[str] = ()

    def setup(self, wen: Wenmode, /) -> None:
        wen.register_rule(HtmlContainer(disallowed_tags=self.disallowed_tags))
        wen.register_renderer_handlers(handlers)


def configure(*, disallowed_tags: Sequence[str] = ()) -> HtmlContainerPlugin:
    return HtmlContainerPlugin(disallowed_tags=disallowed_tags)


def setup(wen: Wenmode, /) -> None:
    configure().setup(wen)
