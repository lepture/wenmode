from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Literal
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer

from .._declaratives import InlineLiteral
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class InlineMathNode(Literal):
    """Inline math node."""

    type: str = 'inlineMath'


def render_html_inline_math(renderer: HTMLRenderer, node: InlineMathNode, context: HTMLRenderContext) -> str:
    return f'<span class="math math-inline">{renderer.escape_html(node.value)}</span>'


def render_markdown_inline_math(renderer: MarkdownRenderer, node: InlineMathNode, context: RenderContext) -> str:
    return f'${node.value}$'


def render_rst_inline_math(renderer: RSTRenderer, node: InlineMathNode, context: RSTRenderContext) -> str:
    return f':math:`{renderer.escape_interpreted_text(node.value)}`'


def render_asciidoc_inline_math(
    renderer: AsciiDocRenderer, node: InlineMathNode, context: AsciiDocRenderContext
) -> str:
    return f'stem:[{node.value}]'


nodes = [InlineMathNode]
rules = [
    InlineLiteral(
        name='inline_math',
        node=InlineMathNode,
        opener='$',
        closer='$',
        reject_closing_before_digit=True,
        reject_adjacent_delimiter=True,
    )
]
handlers: RendererHandlers = {
    'html': {InlineMathNode.type: render_html_inline_math},
    'markdown': {InlineMathNode.type: render_markdown_inline_math},
    'rst': {InlineMathNode.type: render_rst_inline_math},
    'asciidoc': {InlineMathNode.type: render_asciidoc_inline_math},
}


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
