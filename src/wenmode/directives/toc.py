from __future__ import annotations

from collections.abc import Iterable
from typing import TYPE_CHECKING

from wenmode.ast import plain_text
from wenmode.nodes import LeafDirective
from wenmode.toc import collect_toc, render_toc_list

from .util import append_class

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer


class TableOfContents:
    """Render ``toc`` leaf directives as HTML tables of contents.

    :param names: Directive names handled by this renderer.
    """

    node_type = 'leafDirective'

    def __init__(self, names: Iterable[str] = ('toc',)) -> None:
        self.names = frozenset(names)

    def render(self, renderer: HTMLRenderer, node: LeafDirective, context: HTMLRenderContext) -> str:
        if context.root is None:
            return ''

        attributes = dict(node.attributes or {})
        min_depth = parse_depth(attributes, ('min', 'min-depth', 'min_depth'), 1)
        max_depth = parse_depth(attributes, ('max', 'max-depth', 'max_depth'), 6)
        if 'label' in attributes:
            label_attribute = attributes.pop('label')
        else:
            label_attribute = None
        label = plain_text(node.children) or label_attribute or 'Table of contents'
        items = collect_toc(context.root, min_depth=min_depth, max_depth=max_depth)
        if not items:
            return ''

        attributes.pop('min', None)
        attributes.pop('min-depth', None)
        attributes.pop('min_depth', None)
        attributes.pop('max', None)
        attributes.pop('max-depth', None)
        attributes.pop('max_depth', None)
        attributes['aria-label'] = label
        attributes['class'] = append_class(attributes.get('class'), 'toc')
        return f'<nav{renderer.render_attrs(attributes)}>\n{render_toc_list(items)}</nav>\n'


def parse_depth(attributes: dict[str, str], keys: tuple[str, ...], default: int) -> int:
    for key in keys:
        value = attributes.get(key)
        if value is None:
            continue
        try:
            return max(1, min(6, int(value)))
        except ValueError:
            return default
    return default
