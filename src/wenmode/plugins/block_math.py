from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Literal
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block

from .._declarative import BlockFenced, DeclarativePluginSpec, install_declarative
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class MathNode(Literal):
    """Display math block node."""

    type: str = 'math'


def render_html_math(renderer: HTMLRenderer, node: MathNode, context: HTMLRenderContext) -> str:
    return f'<div class="math math-display">{renderer.escape_html(node.value)}</div>\n'


def render_markdown_math(renderer: MarkdownRenderer, node: MathNode, context: RenderContext) -> str:
    if node.value.endswith('\n'):
        value = node.value
    else:
        value = node.value + '\n'
    return f'$$\n{value}$$\n\n'


def render_rst_math(renderer: RSTRenderer, node: MathNode, context: RSTRenderContext) -> str:
    if node.value.endswith('\n'):
        value = node.value
    else:
        value = node.value + '\n'
    return '.. math::\n\n' + indent_block(value.rstrip('\n'), '   ') + '\n\n'


def render_asciidoc_math(renderer: AsciiDocRenderer, node: MathNode, context: AsciiDocRenderContext) -> str:
    value = node.value.rstrip('\n')
    if value:
        return '[stem]\n++++\n' + value + '\n++++\n\n'
    return '[stem]\n++++\n++++\n\n'


_spec = DeclarativePluginSpec(
    name='block_math',
    nodes=[MathNode],
    syntax=[
        BlockFenced(
            name='math_block',
            node=MathNode,
            opener='$$',
            closer='$$',
            allow_opener_content=True,
        )
    ],
    renderers={},
)

nodes = _spec.nodes
handlers: RendererHandlers = {
    'html': {MathNode.type: render_html_math},
    'markdown': {MathNode.type: render_markdown_math},
    'rst': {MathNode.type: render_rst_math},
    'asciidoc': {MathNode.type: render_asciidoc_math},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    install_declarative(wenmode, _spec, **options)
    wenmode.register_renderer_handlers(handlers)
