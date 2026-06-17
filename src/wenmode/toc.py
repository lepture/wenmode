from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

from .headings import iter_headings, plain_text
from .nodes import Node


@dataclass
class TocItem:
    id: str
    title: str
    depth: int
    children: list[TocItem] = field(default_factory=list)


def collect_toc(node: Node, *, min_depth: int = 1, max_depth: int = 6) -> list[TocItem]:
    items: list[TocItem] = []
    stack: list[TocItem] = []

    for heading in iter_headings(node):
        if not (min_depth <= heading.depth <= max_depth):
            continue
        identifier = heading.data.get('id') if heading.data else None
        if not isinstance(identifier, str):
            continue

        item = TocItem(id=identifier, title=plain_text(heading.children), depth=heading.depth)
        while stack and stack[-1].depth >= item.depth:
            stack.pop()
        if stack:
            stack[-1].children.append(item)
        else:
            items.append(item)
        stack.append(item)

    return items


def render_toc_html(items: list[TocItem], *, label: str = 'Table of contents') -> str:
    if not items:
        return ''
    return f'<nav class="toc" aria-label="{escape(label, quote=True)}">\n{render_toc_list(items)}</nav>\n'


def render_toc_list(items: list[TocItem]) -> str:
    parts = ['<ol>\n']
    for item in items:
        parts.append(
            f'<li><a href="#{escape(item.id, quote=True)}">{escape(item.title)}</a>'
            + (f'\n{render_toc_list(item.children)}' if item.children else '')
            + '</li>\n'
        )
    parts.append('</ol>\n')
    return ''.join(parts)
