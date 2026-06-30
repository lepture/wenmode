from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from wenmode.nodes import Node, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.markdown import render_prefixed_block
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules.base import BlockRule, InlineRule, Rule
from wenmode.rules.blocks.util import parse_shallow_block
from wenmode.state import BlockState
from wenmode.utils import expand_leading_tabs

from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

BLOCK_SPOILER_RE = re.compile(r'[ \t]{0,3}>! ?(.*)')


@dataclass
class BlockSpoilerNode(Parent):
    """Block spoiler container node."""

    type: str = 'blockSpoiler'


@dataclass
class InlineSpoilerNode(Parent):
    """Inline spoiler node."""

    type: str = 'inlineSpoiler'


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


class InlineSpoilerRule(InlineRule):
    """Parse spoiler spans delimited by ``>!`` and ``!<``."""

    name = 'inline_spoiler'
    pattern = r'>!'
    trigger_chars = '>'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        parsed = parse_spoiler_span(text, match.start())
        if parsed is None:
            return None, match.start()

        spoiler_text, content_start, content_end, end = parsed
        return (
            InlineSpoilerNode(
                children=parser.parse_inlines(
                    spoiler_text,
                    state,
                    source=parser.inline_source(text, state, content_start, content_end),
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
        if '\n' in value:
            return None
        return value, start, end

    for index, char in reversed(list(enumerate(text))):
        if char != '\n':
            return char, index, index + 1
    return None


def render_html_block(renderer: HTMLRenderer, node: BlockSpoilerNode, context: HTMLRenderContext) -> str:
    return '<div class="spoiler">\n' + renderer.render_children(node.children, context) + '</div>\n'


def render_html_inline(renderer: HTMLRenderer, node: InlineSpoilerNode, context: HTMLRenderContext) -> str:
    return f'<span class="spoiler">{renderer.render_children(node.children, context)}</span>'


def render_markdown_block(renderer: MarkdownRenderer, node: BlockSpoilerNode, context: RenderContext) -> str:
    return render_prefixed_block(renderer, node, '>!', context)


def render_markdown_inline(renderer: MarkdownRenderer, node: InlineSpoilerNode, context: RenderContext) -> str:
    return f'>! {renderer.render_children(node.children, context)} !<'


def render_rst_block(renderer: RSTRenderer, node: BlockSpoilerNode, context: RSTRenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return '.. admonition:: Spoiler\n\n'
    return '.. admonition:: Spoiler\n\n' + indent_block(body, '   ') + '\n\n'


def render_rst_inline(renderer: RSTRenderer, node: InlineSpoilerNode, context: RSTRenderContext) -> str:
    return renderer.render_children(node.children, context)


def render_asciidoc_block(
    renderer: AsciiDocRenderer, node: BlockSpoilerNode, context: AsciiDocRenderContext
) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return '[.spoiler]\n--\n--\n\n'
    return '[.spoiler]\n--\n' + body + '\n--\n\n'


def render_asciidoc_inline(
    renderer: AsciiDocRenderer, node: InlineSpoilerNode, context: AsciiDocRenderContext
) -> str:
    return f'[.spoiler]#{renderer.render_children(node.children, context)}#'


nodes = {BlockSpoilerNode.type: BlockSpoilerNode, InlineSpoilerNode.type: InlineSpoilerNode}
rules: list[type[Rule] | Rule] = [BlockSpoilerRule, InlineSpoilerRule]
handlers: RendererHandlers = {
    'html': {BlockSpoilerNode.type: render_html_block, InlineSpoilerNode.type: render_html_inline},
    'markdown': {BlockSpoilerNode.type: render_markdown_block, InlineSpoilerNode.type: render_markdown_inline},
    'rst': {BlockSpoilerNode.type: render_rst_block, InlineSpoilerNode.type: render_rst_inline},
    'asciidoc': {BlockSpoilerNode.type: render_asciidoc_block, InlineSpoilerNode.type: render_asciidoc_inline},
}


def setup(wenmode: Wenmode, block: bool = True, inline: bool = True, **options: Any) -> None:
    selected_rules: list[type[Rule] | Rule] = []
    if block:
        selected_rules.append(BlockSpoilerRule)
    if inline:
        selected_rules.append(InlineSpoilerRule)
    wenmode.register_rules(selected_rules)
    wenmode.register_renderer_handlers(handlers)
