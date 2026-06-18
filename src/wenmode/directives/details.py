from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from wenmode.nodes import ContainerDirective

from .util import split_directive_label

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer


class Details:
    """Render ``details`` container directives as HTML ``details`` elements.

    :param names: Directive names handled by this renderer.
    """

    node_type = 'containerDirective'

    def __init__(self, names: Iterable[str] = ('details',)) -> None:
        self.names = frozenset(names)

    def render(self, renderer: HTMLRenderer, node: ContainerDirective, context: HTMLRenderContext) -> str:
        label, children = split_directive_label(node)
        parts = [f'<details{renderer.render_attrs(node.attributes or {})}>\n']
        if label is not None:
            parts.append(f'<summary>{renderer.render_children(label.children, context)}</summary>\n')
        parts.append(renderer.render_children(children, context))
        parts.append('</details>\n')
        return ''.join(parts)
