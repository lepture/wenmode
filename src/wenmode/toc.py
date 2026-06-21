from __future__ import annotations

from dataclasses import dataclass, field
from html import escape

from .ast import plain_text
from .headings import iter_headings
from .nodes import Node


@dataclass
class TocItem:
    """One table-of-contents entry."""

    id: str
    title: str
    depth: int
    children: list[TocItem] = field(default_factory=list)


def collect_toc(node: Node, *, min_depth: int = 1, max_depth: int = 6) -> list[TocItem]:
    """Collect heading nodes with IDs into a nested table of contents.

    :param node: Root or subtree to inspect.
    :param min_depth: Minimum heading depth to include.
    :param max_depth: Maximum heading depth to include.
    :returns: Nested table-of-contents items.
    """
    items: list[TocItem] = []
    stack: list[TocItem] = []

    for heading in iter_headings(node):
        if not (min_depth <= heading.depth <= max_depth):
            continue
        if heading.data:
            identifier = heading.data.get('id')
        else:
            identifier = None
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
    """Render table-of-contents items as an HTML ``nav`` element.

    :param items: Items returned by :func:`collect_toc`.
    :param label: Accessible label for the navigation element.
    :returns: HTML string, or an empty string when ``items`` is empty.
    """
    if not items:
        return ''
    return f'<nav class="toc" aria-label="{escape(label, quote=True)}">\n{render_toc_list(items)}</nav>\n'


def render_toc_list(items: list[TocItem]) -> str:
    """Render table-of-contents items as a nested ordered list."""
    parts = ['<ol>\n']
    for item in items:
        if item.children:
            child_list = f'\n{render_toc_list(item.children)}'
        else:
            child_list = ''
        parts.append(f'<li><a href="#{escape(item.id, quote=True)}">{escape(item.title)}</a>' + child_list + '</li>\n')
    parts.append('</ol>\n')
    return ''.join(parts)
