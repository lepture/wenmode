from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from wenmode.nodes import TextDirective

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer


class Abbreviation:
    node_type = 'textDirective'

    def __init__(self, names: Iterable[str] = ('abbr',)) -> None:
        self.names = frozenset(names)

    def render(self, renderer: HTMLRenderer, node: TextDirective, context: HTMLRenderContext) -> str:
        attributes = dict(node.attributes or {})
        if 'title' not in attributes:
            return renderer.render_children(node.children, context)
        return f'<abbr{renderer.render_attrs(attributes)}>{renderer.render_children(node.children, context)}</abbr>'
