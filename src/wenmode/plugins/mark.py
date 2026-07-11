from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Parent
from wenmode.renderers import BaseRenderer, RenderContext

from .._declaratives import InlineDelimited
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class MarkNode(Parent):
    """Highlighted text node."""

    type: str = 'mark'


nodes = [MarkNode]
rules = [
    InlineDelimited(
        name='mark',
        node=MarkNode,
        opener='==',
        closer='==',
        trigger_chars='=',
    )
]
handlers: RendererHandlers = {
    'html': {MarkNode.type: lambda renderer, node, context: render_html_mark(renderer, node, context)},
    'markdown': {MarkNode.type: lambda renderer, node, context: render_markdown_mark(renderer, node, context)},
    'rst': {MarkNode.type: lambda renderer, node, context: render_children(renderer, node, context)},
    'asciidoc': {MarkNode.type: lambda renderer, node, context: render_asciidoc_mark(renderer, node, context)},
}


def render_html_mark(renderer: BaseRenderer, node: MarkNode, context: RenderContext) -> str:
    return f'<mark>{renderer.render_children(node.children, context)}</mark>'


def render_markdown_mark(renderer: BaseRenderer, node: MarkNode, context: RenderContext) -> str:
    return f'=={renderer.render_children(node.children, context)}=='


def render_children(renderer: BaseRenderer, node: MarkNode, context: RenderContext) -> str:
    return renderer.render_children(node.children, context)


def render_asciidoc_mark(renderer: BaseRenderer, node: MarkNode, context: RenderContext) -> str:
    return f'#{renderer.render_children(node.children, context)}#'


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
