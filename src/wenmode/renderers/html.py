from __future__ import annotations

import re
from collections.abc import Mapping

from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    Html,
    HtmlAttrValue,
    List,
    ListItem,
    Node,
    Paragraph,
    Root,
    Text,
)

from .base import BaseRenderer


class HTMLRenderer(BaseRenderer):
    def __init__(self, escape: bool = True) -> None:
        self.escape_enabled = escape

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
                    parts.append(self.render_children(child.children))
                    if index < len(item.children) - 1:
                        parts.append('\n')
                else:
                    parts.append(self.render(child))
            return prefix + ''.join(parts) + '</li>\n'
        return '<li>\n' + self.render_children(item.children) + '</li>\n'

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


@HTMLRenderer.register('break')
def render_break(renderer: HTMLRenderer, node: Break) -> str:
    return '<br />\n'
