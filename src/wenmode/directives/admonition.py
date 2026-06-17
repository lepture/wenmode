from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from wenmode.nodes import ContainerDirective

from .util import split_directive_label

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer


class Admonition:
    node_type = 'containerDirective'

    def __init__(self, names: Iterable[str] = ('note', 'tip', 'caution', 'danger')) -> None:
        self.names = frozenset(names)

    def render(self, renderer: HTMLRenderer, node: ContainerDirective, context: HTMLRenderContext) -> str:
        label, children = split_directive_label(node)
        class_name = f'admonition admonition-{node.name}'
        attrs = dict(node.attributes or {})
        attrs['class'] = append_class(attrs.get('class'), class_name)

        parts = [f'<aside{renderer.render_attrs(attrs)}>\n']
        if label is not None:
            parts.append(f'<p class="admonition-title">{renderer.render_children(label.children, context)}</p>\n')
        parts.append(renderer.render_children(children, context))
        parts.append('</aside>\n')
        return ''.join(parts)


def append_class(current: str | None, value: str) -> str:
    return f'{current} {value}' if current else value
