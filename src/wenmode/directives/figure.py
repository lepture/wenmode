from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import ContainerDirective, DirectiveNode

from .util import split_directive_label

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderer


class Figure:
    def __init__(self, name: str = 'figure') -> None:
        self.name = name

    def render(self, renderer: HTMLRenderer, node: DirectiveNode) -> str | None:
        if not isinstance(node, ContainerDirective) or node.name != self.name:
            return None

        label, children = split_directive_label(node)
        parts = [f'<figure{renderer.render_attrs(node.attributes or {})}>\n']
        parts.append(renderer.render_children(children))
        if label is not None:
            parts.append(f'<figcaption>{renderer.render_children(label.children)}</figcaption>\n')
        parts.append('</figure>\n')
        return ''.join(parts)
