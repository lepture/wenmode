from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Node, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext, render_node_children
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.rules.base import InlineRule, Rule
from wenmode.state import BlockState

from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


@dataclass
class InlineSpoilerNode(Parent):
    """Inline spoiler node."""

    type: str = 'inlineSpoiler'


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


def render_html_inline(renderer: HTMLRenderer, node: InlineSpoilerNode, context: HTMLRenderContext) -> str:
    return f'<span class="spoiler">{renderer.render_children(node.children, context)}</span>'


def render_markdown_inline(renderer: MarkdownRenderer, node: InlineSpoilerNode, context: RenderContext) -> str:
    return f'>! {renderer.render_children(node.children, context)} !<'


def render_asciidoc_inline(
    renderer: AsciiDocRenderer, node: InlineSpoilerNode, context: AsciiDocRenderContext
) -> str:
    return f'[.spoiler]#{renderer.render_children(node.children, context)}#'


nodes = [InlineSpoilerNode]
rules: list[type[Rule] | Rule] = [InlineSpoilerRule]
handlers: RendererHandlers = {
    'html': {InlineSpoilerNode.type: render_html_inline},
    'markdown': {InlineSpoilerNode.type: render_markdown_inline},
    'rst': {InlineSpoilerNode.type: render_node_children},
    'asciidoc': {InlineSpoilerNode.type: render_asciidoc_inline},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
