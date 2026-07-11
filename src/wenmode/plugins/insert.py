from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode._declaratives import InlineDelimited
from wenmode.nodes import Parent
from wenmode.renderers import BaseRenderer, RenderContext

from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class InsertNode(Parent):
    """Inserted text node."""

    type: str = 'insert'


nodes = [InsertNode]
rules = [
    InlineDelimited(
        name='insert',
        node=InsertNode,
        opener='^^',
        closer='^^',
        trigger_chars='^',
    )
]
handlers: RendererHandlers = {
    'html': {InsertNode.type: lambda renderer, node, context: render_html_insert(renderer, node, context)},
    'markdown': {InsertNode.type: lambda renderer, node, context: render_markdown_insert(renderer, node, context)},
    'rst': {InsertNode.type: lambda renderer, node, context: render_children(renderer, node, context)},
    'asciidoc': {InsertNode.type: lambda renderer, node, context: render_asciidoc_insert(renderer, node, context)},
}


def render_html_insert(renderer: BaseRenderer, node: InsertNode, context: RenderContext) -> str:
    return f'<ins>{renderer.render_children(node.children, context)}</ins>'


def render_markdown_insert(renderer: BaseRenderer, node: InsertNode, context: RenderContext) -> str:
    return f'^^{renderer.render_children(node.children, context)}^^'


def render_children(renderer: BaseRenderer, node: InsertNode, context: RenderContext) -> str:
    return renderer.render_children(node.children, context)


def render_asciidoc_insert(renderer: BaseRenderer, node: InsertNode, context: RenderContext) -> str:
    return f'[.underline]#{renderer.render_children(node.children, context)}#'


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
