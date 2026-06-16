from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from wenmode.nodes import ContainerDirective, DirectiveNode

from .util import split_directive_label

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderer


class Admonition:
    def __init__(self, types: Iterable[str] = ('note', 'tip', 'caution', 'danger')) -> None:
        self.types = frozenset(types)

    def render(self, renderer: HTMLRenderer, node: DirectiveNode) -> str | None:
        if not isinstance(node, ContainerDirective) or node.name not in self.types:
            return None

        label, children = split_directive_label(node)
        class_name = f'admonition admonition-{node.name}'
        attrs = dict(node.attributes or {})
        attrs['class'] = append_class(attrs.get('class'), class_name)

        parts = [f'<aside{renderer.render_attrs(attrs)}>\n']
        if label is not None:
            parts.append(f'<p class="admonition-title">{renderer.render_children(label.children)}</p>\n')
        parts.append(renderer.render_children(children))
        parts.append('</aside>\n')
        return ''.join(parts)


def append_class(current: str | None, value: str) -> str:
    return f'{current} {value}' if current else value
