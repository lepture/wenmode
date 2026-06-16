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
    Paragraph,
    Root,
    Strong,
    Text,
    ThematicBreak,
)

from .base import BaseRenderer


class MarkdownRenderer(BaseRenderer):
    def render_list_item(self, item: ListItem, marker: str) -> str:
        if not item.children:
            return marker.rstrip()

        body = self.render_children(item.children).rstrip('\n')
        lines = body.splitlines() or ['']
        indent = ' ' * len(marker)
        parts = [marker + lines[0]]
        parts.extend(indent + line for line in lines[1:])
        return '\n'.join(parts)

    def escape_text(self, value: str) -> str:
        return re.sub(r'([\\`*_{}\[\]<>()#+\-.!|])', r'\\\1', value)

    def escape_destination(self, value: str) -> str:
        if re.search(r'[\s()]', value):
            return '<' + value.replace('\\', '\\\\').replace('<', '\\<').replace('>', '\\>') + '>'
        return value.replace('\\', '\\\\').replace(')', '\\)')

    def escape_title(self, value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"')


@MarkdownRenderer.register('root')
def render_root(renderer: MarkdownRenderer, node: Root) -> str:
    output = renderer.render_children(node.children).rstrip()
    return output + '\n' if output else ''


@MarkdownRenderer.register('paragraph')
def render_paragraph(renderer: MarkdownRenderer, node: Paragraph) -> str:
    return renderer.render_children(node.children) + '\n\n'


@MarkdownRenderer.register('heading')
def render_heading(renderer: MarkdownRenderer, node: Heading) -> str:
    marker = '#' * node.depth
    return f'{marker} {renderer.render_children(node.children)}\n\n'


@MarkdownRenderer.register('blockquote')
def render_blockquote(renderer: MarkdownRenderer, node: Blockquote) -> str:
    body = renderer.render_children(node.children).rstrip('\n')
    if not body:
        return '>\n\n'
    lines = body.splitlines()
    return '\n'.join('> ' + line if line else '>' for line in lines) + '\n\n'


@MarkdownRenderer.register('list')
def render_list(renderer: MarkdownRenderer, node: List) -> str:
    parts: list[str] = []
    start = node.start or 1
    separator = '\n\n' if node.spread else '\n'

    for index, child in enumerate(node.children):
        if not isinstance(child, ListItem):
            parts.append(renderer.render(child).rstrip('\n'))
            continue
        marker = f'{start + index}. ' if node.ordered else '- '
        parts.append(renderer.render_list_item(child, marker))

    return separator.join(parts) + '\n\n'


@MarkdownRenderer.register('listItem')
def render_list_item(renderer: MarkdownRenderer, node: ListItem) -> str:
    return renderer.render_children(node.children)


@MarkdownRenderer.register('code')
def render_code(renderer: MarkdownRenderer, node: Code) -> str:
    longest_fence = max((len(match.group(0)) for match in re.finditer(r'`+', node.value)), default=2)
    fence = '`' * max(3, longest_fence + 1)
    info = node.lang or ''
    if node.meta:
        info = (info + ' ' + node.meta).strip()
    value = node.value if node.value.endswith('\n') else node.value + '\n'
    return f'{fence}{info}\n{value}{fence}\n\n'


@MarkdownRenderer.register('thematicBreak')
def render_thematic_break(renderer: MarkdownRenderer, node: ThematicBreak) -> str:
    return '---\n\n'


@MarkdownRenderer.register('html')
def render_html(renderer: MarkdownRenderer, node: Html) -> str:
    if node.value.endswith('\n'):
        return node.value.rstrip('\n') + '\n\n'
    return node.value


@MarkdownRenderer.register('text')
def render_text(renderer: MarkdownRenderer, node: Text) -> str:
    return renderer.escape_text(node.value)


@MarkdownRenderer.register('inlineCode')
def render_inline_code(renderer: MarkdownRenderer, node: InlineCode) -> str:
    longest_fence = max((len(match.group(0)) for match in re.finditer(r'`+', node.value)), default=0)
    fence = '`' * (longest_fence + 1)
    needs_padding = node.value.startswith(('`', ' ')) or node.value.endswith(('`', ' '))
    if needs_padding:
        return f'{fence} {node.value} {fence}'
    return f'{fence}{node.value}{fence}'


@MarkdownRenderer.register('strong')
def render_strong(renderer: MarkdownRenderer, node: Strong) -> str:
    return f'**{renderer.render_children(node.children)}**'


@MarkdownRenderer.register('emphasis')
def render_emphasis(renderer: MarkdownRenderer, node: Emphasis) -> str:
    return f'*{renderer.render_children(node.children)}*'


@MarkdownRenderer.register('link')
def render_link(renderer: MarkdownRenderer, node: Link) -> str:
    title = f' "{renderer.escape_title(node.title)}"' if node.title else ''
    return f'[{renderer.render_children(node.children)}]({renderer.escape_destination(node.url)}{title})'


@MarkdownRenderer.register('image')
def render_image(renderer: MarkdownRenderer, node: Image) -> str:
    title = f' "{renderer.escape_title(node.title)}"' if node.title else ''
    return f'![{renderer.escape_text(node.alt)}]({renderer.escape_destination(node.url)}{title})'


@MarkdownRenderer.register('break')
def render_break(renderer: MarkdownRenderer, node: Break) -> str:
    return '  \n'
