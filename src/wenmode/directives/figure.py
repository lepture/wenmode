from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from wenmode.nodes import ContainerDirective

from .util import split_directive_label

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer


class Figure:
    node_type = 'containerDirective'

    def __init__(self, names: Iterable[str] = ('figure',)) -> None:
        self.names = frozenset(names)

    def render(self, renderer: HTMLRenderer, node: ContainerDirective, context: HTMLRenderContext) -> str:
        label, children = split_directive_label(node)
        parts = [f'<figure{renderer.render_attrs(node.attributes or {})}>\n']
        parts.append(renderer.render_children(children, context))
        if label is not None:
            parts.append(f'<figcaption>{renderer.render_children(label.children, context)}</figcaption>\n')
        parts.append('</figure>\n')
        return ''.join(parts)
