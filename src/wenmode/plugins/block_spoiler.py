from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from wenmode.nodes import Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.markdown import render_prefixed_block
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules.base import BlockRule, Rule
from wenmode.rules.blocks.util import parse_shallow_block
from wenmode.utils import expand_leading_tabs

from .._parser.state import BlockState
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

BLOCK_SPOILER_RE = re.compile(r'[ \t]{0,3}>! ?(.*)')


@dataclass
class BlockSpoilerNode(Parent):
    """Block spoiler container node."""

    block: ClassVar[bool] = True
    type: str = 'blockSpoiler'


class BlockSpoilerRule(BlockRule):
    """Parse ``>!`` block spoiler containers."""

    order: ClassVar[int] = 90
    name = 'block_spoiler'
    pattern = r'[ \t]{0,3}>!'

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> BlockSpoilerNode:
        if state.depth >= parser.max_container_depth - 1:
            return BlockSpoilerNode(children=parse_shallow_block(parser, BLOCK_SPOILER_RE, state))

        lines: list[str] = []
        source = state.source.collect()
        while not state.done:
            spoiler = BLOCK_SPOILER_RE.match(state.line)
            if spoiler is None:
                break
            if state.line.endswith('\n'):
                line_end = '\n'
            else:
                line_end = ''
            text = expand_leading_tabs(spoiler.group(1), 2) + line_end
            lines.append(text)
            source.add(state.index, spoiler.start(1), text)
            state.advance()

        text = ''.join(lines)
        return BlockSpoilerNode(children=parser.parse_blocks(text, parent_state=state, source=source.map()))


def render_html_block(renderer: HTMLRenderer, node: BlockSpoilerNode, context: HTMLRenderContext) -> str:
    return '<div class="spoiler">\n' + renderer.render_children(node.children, context) + '</div>\n'


def render_markdown_block(renderer: MarkdownRenderer, node: BlockSpoilerNode, context: RenderContext) -> str:
    return render_prefixed_block(renderer, node, '>!', context)


def render_rst_block(renderer: RSTRenderer, node: BlockSpoilerNode, context: RSTRenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return '.. admonition:: Spoiler\n\n'
    return '.. admonition:: Spoiler\n\n' + indent_block(body, '   ') + '\n\n'


def render_asciidoc_block(
    renderer: AsciiDocRenderer, node: BlockSpoilerNode, context: AsciiDocRenderContext
) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return '[.spoiler]\n--\n--\n\n'
    return '[.spoiler]\n--\n' + body + '\n--\n\n'


nodes = [BlockSpoilerNode]
rules: list[type[Rule] | Rule] = [BlockSpoilerRule]
handlers: RendererHandlers = {
    'html': {BlockSpoilerNode.type: render_html_block},
    'markdown': {BlockSpoilerNode.type: render_markdown_block},
    'rst': {BlockSpoilerNode.type: render_rst_block},
    'asciidoc': {BlockSpoilerNode.type: render_asciidoc_block},
}


def setup(wen: Wenmode, **options: Any) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
