from __future__ import annotations

import re
from collections.abc import Mapping
from urllib.parse import urlsplit

from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    Delete,
    Html,
    HtmlAttrValue,
    Image,
    Link,
    List,
    ListItem,
    Node,
    Paragraph,
    Root,
    Table,
    TableCell,
    TableRow,
    Text,
)

from .base import BaseRenderer


class HTMLRenderer(BaseRenderer):
    allowed_url_schemes = frozenset({'http', 'https', 'irc', 'ircs', 'mailto', 'tel'})

    def __init__(self, escape: bool = True, sanitize_urls: bool = True) -> None:
        self.escape_enabled = escape
        self.sanitize_urls = sanitize_urls

    def render_list_item(self, item: Node, loose: bool) -> str:
        if not isinstance(item, ListItem):
            return self.render(item)
        if not item.children:
            return '<li></li>\n'
        if not loose:
            prefix = '<li>' if isinstance(item.children[0], Paragraph) else '<li>\n'
            parts: list[str] = []
            for index, child in enumerate(item.children):
                if isinstance(child, Paragraph):
                    marker = self.render_task_marker(item) if index == 0 else ''
                    parts.append(marker)
                    parts.append(self.render_children(child.children))
                    if index < len(item.children) - 1:
                        parts.append('\n')
                else:
                    if index == 0:
                        parts.append(self.render_task_marker(item))
                    parts.append(self.render(child))
            return prefix + ''.join(parts) + '</li>\n'
        return '<li>\n' + self.render_loose_list_item_children(item) + '</li>\n'

    def render_loose_list_item_children(self, item: ListItem) -> str:
        parts: list[str] = []
        for index, child in enumerate(item.children):
            if index == 0 and isinstance(child, Paragraph) and item.checked is not None:
                parts.append('<p>' + self.render_task_marker(item) + self.render_children(child.children) + '</p>\n')
            else:
                if index == 0 and item.checked is not None:
                    parts.append(self.render_task_marker(item))
                parts.append(self.render(child))
        return ''.join(parts)

    def render_task_marker(self, item: ListItem) -> str:
        if item.checked is None:
            return ''
        if item.checked:
            return '<input checked="" disabled="" type="checkbox"> '
        return '<input disabled="" type="checkbox"> '

    def escape(self, value: str) -> str:
        if not self.escape_enabled:
            return value
        return self.escape_html(value)

    def escape_html(self, value: str) -> str:
        return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def render_unknown(self, node: Node) -> str:
        tag = node.get_html_tag()
        if tag is not None:
            return self.render_element(node, tag)
        return super().render_unknown(node)

    def render_element(self, node: Node, tag: str) -> str:
        attrs = self.render_attrs(node.get_html_attrs())
        if node.html_void:
            return f'<{tag}{attrs} />' + ('\n' if node.block else '')

        content = self.render_element_content(node)
        return f'<{tag}{attrs}>{content}</{tag}>' + ('\n' if node.block else '')

    def render_element_content(self, node: Node) -> str:
        children = getattr(node, 'children', None)
        if isinstance(children, list):
            return self.render_children(children)

        value = getattr(node, 'value', None)
        if isinstance(value, str):
            return self.escape_html(value)

        return ''

    def render_attrs(self, attrs: Mapping[str, HtmlAttrValue]) -> str:
        rendered: list[str] = []
        for name, value in attrs.items():
            if value is None or value is False:
                continue
            if value is True:
                rendered.append(name)
            else:
                rendered.append(f'{name}="{self.escape_html(str(value))}"')
        return (' ' + ' '.join(rendered)) if rendered else ''

    def sanitize_url(self, value: str) -> str | None:
        if not self.sanitize_urls:
            return value

        normalized = ''.join(char for char in value.strip() if char > ' ')
        scheme = urlsplit(normalized).scheme.lower()
        if scheme and scheme not in self.allowed_url_schemes:
            return None
        return value


@HTMLRenderer.register('root')
def render_root(renderer: HTMLRenderer, node: Root) -> str:
    return renderer.render_children(node.children)


@HTMLRenderer.register('blockquote')
def render_blockquote(renderer: HTMLRenderer, node: Blockquote) -> str:
    return '<blockquote>\n' + renderer.render_children(node.children) + '</blockquote>\n'


@HTMLRenderer.register('list')
def render_list(renderer: HTMLRenderer, node: List) -> str:
    tag = 'ol' if node.ordered else 'ul'
    start = f' start="{node.start}"' if node.ordered and node.start not in (None, 1) else ''
    return (
        f'<{tag}{start}>\n'
        + ''.join(renderer.render_list_item(child, node.spread) for child in node.children)
        + f'</{tag}>\n'
    )


@HTMLRenderer.register('listItem')
def render_list_item(renderer: HTMLRenderer, node: ListItem) -> str:
    return renderer.render_list_item(node, node.spread)


@HTMLRenderer.register('delete')
def render_delete(renderer: HTMLRenderer, node: Delete) -> str:
    return f'<del>{renderer.render_children(node.children)}</del>'


@HTMLRenderer.register('table')
def render_table(renderer: HTMLRenderer, node: Table) -> str:
    if not node.children:
        return '<table>\n</table>\n'

    header = node.children[0]
    body = node.children[1:]
    output = ['<table>\n<thead>\n', render_table_row(renderer, header, 'th', node.align), '</thead>\n']
    if body:
        output.append('<tbody>\n')
        output.extend(render_table_row(renderer, row, 'td', node.align) for row in body)
        output.append('</tbody>\n')
    output.append('</table>\n')
    return ''.join(output)


@HTMLRenderer.register('tableRow')
def render_table_row_node(renderer: HTMLRenderer, node: TableRow) -> str:
    return render_table_row(renderer, node, 'td', [])


@HTMLRenderer.register('tableCell')
def render_table_cell_node(renderer: HTMLRenderer, node: TableCell) -> str:
    return f'<td>{renderer.render_children(node.children)}</td>'


def render_table_row(renderer: HTMLRenderer, row: Node, tag: str, align: list[str | None]) -> str:
    if not isinstance(row, TableRow):
        return renderer.render(row)
    output = ['<tr>\n']
    for index, cell in enumerate(row.children):
        if not isinstance(cell, TableCell):
            output.append(renderer.render(cell))
            continue
        attrs = {'align': align[index]} if index < len(align) and align[index] is not None else {}
        output.append(f'<{tag}{renderer.render_attrs(attrs)}>{renderer.render_children(cell.children)}</{tag}>\n')
    output.append('</tr>\n')
    return ''.join(output)


@HTMLRenderer.register('code')
def render_code(renderer: HTMLRenderer, node: Code) -> str:
    lang = f' class="language-{renderer.escape_html(node.lang)}"' if node.lang else ''
    return f'<pre><code{lang}>{renderer.escape_html(node.value)}</code></pre>\n'


@HTMLRenderer.register('html')
def render_html(renderer: HTMLRenderer, node: Html) -> str:
    return renderer.escape(node.value)


@HTMLRenderer.register('text')
def render_text(renderer: HTMLRenderer, node: Text) -> str:
    return renderer.escape_html(re.sub(r'(?<! ) (?=\r?\n)', '', node.value))


@HTMLRenderer.register('link')
def render_link(renderer: HTMLRenderer, node: Link) -> str:
    attrs = node.get_html_attrs()
    href = renderer.sanitize_url(node.url)
    if href is None:
        attrs.pop('href', None)
    else:
        attrs['href'] = href
    return f'<a{renderer.render_attrs(attrs)}>{renderer.render_children(node.children)}</a>'


@HTMLRenderer.register('image')
def render_image(renderer: HTMLRenderer, node: Image) -> str:
    attrs = node.get_html_attrs()
    src = renderer.sanitize_url(node.url)
    if src is None:
        attrs.pop('src', None)
    else:
        attrs['src'] = src
    return f'<img{renderer.render_attrs(attrs)} />'


@HTMLRenderer.register('break')
def render_break(renderer: HTMLRenderer, node: Break) -> str:
    return '<br />\n'
