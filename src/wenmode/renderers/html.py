from __future__ import annotations

import re

from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    Emphasis,
    Heading,
    Html,
    Image,
    InlineCode,
    Link,
    List,
    ListItem,
    Node,
    Paragraph,
    Root,
    Strong,
    Text,
    ThematicBreak,
)


class HTMLRenderer:
    def render(self, node: Node) -> str:
        if isinstance(node, Root):
            return self.render_children(node.children)
        if isinstance(node, Paragraph):
            return f'<p>{self.render_children(node.children)}</p>\n'
        if isinstance(node, Heading):
            return f'<h{node.depth}>{self.render_children(node.children)}</h{node.depth}>\n'
        if isinstance(node, Blockquote):
            return '<blockquote>\n' + self.render_children(node.children) + '</blockquote>\n'
        if isinstance(node, List):
            tag = 'ol' if node.ordered else 'ul'
            start = f' start="{node.start}"' if node.ordered and node.start not in (None, 1) else ''
            return (
                f'<{tag}{start}>\n'
                + ''.join(self.render_list_item(child, node.spread) for child in node.children)
                + f'</{tag}>\n'
            )
        if isinstance(node, ListItem):
            return self.render_list_item(node, node.spread)
        if isinstance(node, Code):
            lang = f' class="language-{self.escape(node.lang)}"' if node.lang else ''
            return f'<pre><code{lang}>{self.escape(node.value)}</code></pre>\n'
        if isinstance(node, ThematicBreak):
            return '<hr />\n'
        if isinstance(node, Html):
            return node.value
        if isinstance(node, Text):
            return self.escape(re.sub(r'(?<! ) (?=\r?\n)', '', node.value))
        if isinstance(node, InlineCode):
            return f'<code>{self.escape(node.value)}</code>'
        if isinstance(node, Strong):
            return f'<strong>{self.render_children(node.children)}</strong>'
        if isinstance(node, Emphasis):
            return f'<em>{self.render_children(node.children)}</em>'
        if isinstance(node, Link):
            title = f' title="{self.escape(node.title)}"' if node.title else ''
            return f'<a href="{self.escape(node.url)}"{title}>{self.render_children(node.children)}</a>'
        if isinstance(node, Image):
            title = f' title="{self.escape(node.title)}"' if node.title else ''
            return f'<img src="{self.escape(node.url)}" alt="{self.escape(node.alt)}"{title} />'
        if isinstance(node, Break):
            return '<br />\n'
        return ''

    def render_children(self, children: list[Node]) -> str:
        return ''.join(self.render(child) for child in children)

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
        return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
