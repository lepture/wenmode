from __future__ import annotations

import re

from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    Delete,
    Emphasis,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    InlineMath,
    Link,
    List,
    ListItem,
    Math,
    Node,
    Paragraph,
    Root,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    ThematicBreak,
)

from .base import BaseRenderer

ESCAPABLE_TEXT_RE = re.compile(r'([\\`*_{}\[\]<>()#+\-.!|])')
DESTINATION_WRAP_RE = re.compile(r'[\s()]')


class MarkdownRenderer(BaseRenderer):
    def render_list_item(self, item: ListItem, marker: str) -> str:
        if item.checked is not None:
            marker += '[x] ' if item.checked else '[ ] '
        if not item.children:
            return marker.rstrip()

        body = self.render_children(item.children).rstrip('\n')
        lines = body.splitlines() or ['']
        indent = ' ' * len(marker)
        parts = [marker + lines[0]]
        parts.extend(indent + line for line in lines[1:])
        return '\n'.join(parts)

    def escape_text(self, value: str) -> str:
        return ESCAPABLE_TEXT_RE.sub(r'\\\1', value)

    def escape_destination(self, value: str) -> str:
        if DESTINATION_WRAP_RE.search(value):
            return '<' + value.replace('\\', '\\\\').replace('<', '\\<').replace('>', '\\>') + '>'
        return value.replace('\\', '\\\\').replace(')', '\\)')

    def escape_title(self, value: str) -> str:
        return value.replace('\\', '\\\\').replace('"', '\\"')

    def render_table_cell_content(self, cell: TableCell) -> str:
        return self.render_children(cell.children).replace('\n', ' ').strip()


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


@MarkdownRenderer.register('delete')
def render_delete(renderer: MarkdownRenderer, node: Delete) -> str:
    return f'~~{renderer.render_children(node.children)}~~'


@MarkdownRenderer.register('table')
def render_table(renderer: MarkdownRenderer, node: Table) -> str:
    if not node.children:
        return ''

    header = normalize_table_row(node.children[0], len(node.align))
    body = [normalize_table_row(row, len(node.align)) for row in node.children[1:]]
    lines = [
        '| ' + ' | '.join(renderer.render_table_cell_content(cell) for cell in header) + ' |',
        '| ' + ' | '.join(delimiter_for_align(align) for align in node.align) + ' |',
    ]
    lines.extend('| ' + ' | '.join(renderer.render_table_cell_content(cell) for cell in row) + ' |' for row in body)
    return '\n'.join(lines) + '\n\n'


@MarkdownRenderer.register('tableRow')
def render_table_row(renderer: MarkdownRenderer, node: TableRow) -> str:
    cells = [cell for cell in node.children if isinstance(cell, TableCell)]
    return '| ' + ' | '.join(renderer.render_table_cell_content(cell) for cell in cells) + ' |\n'


@MarkdownRenderer.register('tableCell')
def render_table_cell(renderer: MarkdownRenderer, node: TableCell) -> str:
    return renderer.render_table_cell_content(node)


def normalize_table_row(row: Node, size: int) -> list[TableCell]:
    cells = [cell for cell in row.children if isinstance(cell, TableCell)] if isinstance(row, TableRow) else []
    if len(cells) < size:
        cells.extend(TableCell() for _ in range(size - len(cells)))
    return cells[:size]


def delimiter_for_align(align: str | None) -> str:
    if align == 'left':
        return ':---'
    if align == 'right':
        return '---:'
    if align == 'center':
        return ':---:'
    return '---'


@MarkdownRenderer.register('code')
def render_code(renderer: MarkdownRenderer, node: Code) -> str:
    longest_fence = max((len(match.group(0)) for match in re.finditer(r'`+', node.value)), default=2)
    fence = '`' * max(3, longest_fence + 1)
    info = node.lang or ''
    if node.meta:
        info = (info + ' ' + node.meta).strip()
    value = node.value if node.value.endswith('\n') else node.value + '\n'
    return f'{fence}{info}\n{value}{fence}\n\n'


@MarkdownRenderer.register('math')
def render_math(renderer: MarkdownRenderer, node: Math) -> str:
    value = node.value if node.value.endswith('\n') else node.value + '\n'
    return f'$$\n{value}$$\n\n'


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


@MarkdownRenderer.register('inlineMath')
def render_inline_math(renderer: MarkdownRenderer, node: InlineMath) -> str:
    return f'${node.value}$'


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


@MarkdownRenderer.register('footnoteReference')
def render_footnote_reference(renderer: MarkdownRenderer, node: FootnoteReference) -> str:
    return f'[^{renderer.escape_text(node.label or node.identifier)}]'


@MarkdownRenderer.register('footnoteDefinition')
def render_footnote_definition(renderer: MarkdownRenderer, node: FootnoteDefinition) -> str:
    label = renderer.escape_text(node.label or node.identifier)
    body = renderer.render_children(node.children).rstrip('\n')
    if not body:
        return f'[^{label}]:\n\n'

    lines = body.splitlines()
    return f'[^{label}]: {lines[0]}\n' + ''.join(f'  {line}\n' for line in lines[1:]) + '\n'
