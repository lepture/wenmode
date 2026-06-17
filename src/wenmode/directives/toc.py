from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import DirectiveNode, LeafDirective
from wenmode.toc import collect_toc, plain_text, render_toc_list

if TYPE_CHECKING:
    from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer


class TableOfContents:
    def __init__(self, name: str = 'toc') -> None:
        self.name = name

    def render(self, renderer: HTMLRenderer, node: DirectiveNode, context: HTMLRenderContext) -> str | None:
        if not isinstance(node, LeafDirective) or node.name != self.name:
            return None
        if context.root is None:
            return ''

        attributes = dict(node.attributes or {})
        min_depth = parse_depth(attributes, ('min', 'min-depth', 'min_depth'), 1)
        max_depth = parse_depth(attributes, ('max', 'max-depth', 'max_depth'), 6)
        label_attribute = attributes.pop('label') if 'label' in attributes else None
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


def append_class(current: str | None, value: str) -> str:
    return f'{current} {value}' if current else value
