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
class InlineSpoilerNode(Parent):
    """Inline spoiler node."""

    type: str = 'inlineSpoiler'


nodes = [InlineSpoilerNode]
rules = [
    InlineDelimited(
        name='inline_spoiler',
        node=InlineSpoilerNode,
        opener='>!',
        closer='!<',
        trigger_chars='>',
        allow_newline=False,
        reject_opening_whitespace=False,
        reject_closing_whitespace=False,
        reject_longer_run=False,
        strip_content=True,
    )
]
handlers: RendererHandlers = {
    'html': {InlineSpoilerNode.type: lambda renderer, node, context: render_html_spoiler(renderer, node, context)},
    'markdown': {InlineSpoilerNode.type: lambda renderer, node, context: render_markdown_spoiler(renderer, node, context)},
    'rst': {InlineSpoilerNode.type: lambda renderer, node, context: render_children(renderer, node, context)},
    'asciidoc': {InlineSpoilerNode.type: lambda renderer, node, context: render_asciidoc_spoiler(renderer, node, context)},
}


def render_html_spoiler(renderer: BaseRenderer, node: InlineSpoilerNode, context: RenderContext) -> str:
    return f'<span class="spoiler">{renderer.render_children(node.children, context)}</span>'


def render_markdown_spoiler(renderer: BaseRenderer, node: InlineSpoilerNode, context: RenderContext) -> str:
    return f'>! {renderer.render_children(node.children, context)} !<'


def render_children(renderer: BaseRenderer, node: InlineSpoilerNode, context: RenderContext) -> str:
    return renderer.render_children(node.children, context)


def render_asciidoc_spoiler(renderer: BaseRenderer, node: InlineSpoilerNode, context: RenderContext) -> str:
    return f'[.spoiler]#{renderer.render_children(node.children, context)}#'


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
