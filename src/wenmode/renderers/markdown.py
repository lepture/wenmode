from __future__ import annotations

import re

from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    ContainerDirective,
    Delete,
    Emphasis,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    InlineMath,
    InlineSpoiler,
    Insert,
    LeafDirective,
    Link,
    List,
    ListItem,
    Mark,
    Math,
    Node,
    Paragraph,
    Parent,
    Root,
    Ruby,
    Strong,
    Subscript,
    Superscript,
    Table,
    TableCell,
    TableRow,
    Text,
    TextDirective,
    ThematicBreak,
)

from .base import BaseRenderer, RenderContext

ESCAPABLE_TEXT_RE = re.compile(r'([\\`*_{}\[\]<>()#+\-.!|])')
DESTINATION_WRAP_RE = re.compile(r'[\s()]')


class MarkdownRenderer(BaseRenderer):
    def render_list_item(self, item: ListItem, marker: str, context: RenderContext) -> str:
        if item.checked is not None:
            marker += '[x] ' if item.checked else '[ ] '
        if not item.children:
            return marker.rstrip()

        body = self.render_children(item.children, context).rstrip('\n')
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

    def render_table_cell_content(self, cell: TableCell, context: RenderContext) -> str:
        return self.render_children(cell.children, context).replace('\n', ' ').strip()

    def render_directive_label(self, node: Node, context: RenderContext) -> str:
        if not isinstance(node, Parent):
            return ''
        return '[' + self.render_children(node.children, context).strip() + ']' if node.children else ''

    def render_directive_attributes(self, attributes: dict[str, str] | None) -> str:
        if not attributes:
            return ''

        parts: list[str] = []
        identifier = attributes.get('id')
        if identifier:
            parts.append('#' + identifier)

        class_name = attributes.get('class')
        if class_name:
            parts.extend('.' + value for value in class_name.split() if value)

        for key, value in attributes.items():
            if key in {'id', 'class'}:
                continue
            if value == '':
                parts.append(key)
            else:
                parts.append(f'{key}={quote_directive_attribute(value)}')

        return '{' + ' '.join(parts) + '}' if parts else ''

    def render_script_children(self, node: Parent, marker: str, context: RenderContext) -> str:
        content = self.render_children(node.children, context)
        return content.replace(' ', '\\ ').replace(marker, '\\' + marker)


@MarkdownRenderer.register('root')
def render_root(renderer: MarkdownRenderer, node: Root, context: RenderContext) -> str:
    output = renderer.render_children(node.children, context).rstrip()
    return output + '\n' if output else ''


@MarkdownRenderer.register('paragraph')
def render_paragraph(renderer: MarkdownRenderer, node: Paragraph, context: RenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n\n'


@MarkdownRenderer.register('heading')
def render_heading(renderer: MarkdownRenderer, node: Heading, context: RenderContext) -> str:
    marker = '#' * node.depth
    return f'{marker} {renderer.render_children(node.children, context)}\n\n'


@MarkdownRenderer.register('blockquote')
def render_blockquote(renderer: MarkdownRenderer, node: Blockquote, context: RenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return '>\n\n'
    lines = body.splitlines()
    return '\n'.join('> ' + line if line else '>' for line in lines) + '\n\n'


@MarkdownRenderer.register('list')
def render_list(renderer: MarkdownRenderer, node: List, context: RenderContext) -> str:
    parts: list[str] = []
    start = node.start or 1
    separator = '\n\n' if node.spread else '\n'

    for index, child in enumerate(node.children):
        if not isinstance(child, ListItem):
            parts.append(renderer.render_node(child, context).rstrip('\n'))
            continue
        marker = f'{start + index}. ' if node.ordered else '- '
        parts.append(renderer.render_list_item(child, marker, context))

    return separator.join(parts) + '\n\n'


@MarkdownRenderer.register('listItem')
def render_list_item(renderer: MarkdownRenderer, node: ListItem, context: RenderContext) -> str:
    return renderer.render_children(node.children, context)


@MarkdownRenderer.register('delete')
def render_delete(renderer: MarkdownRenderer, node: Delete, context: RenderContext) -> str:
    return f'~~{renderer.render_children(node.children, context)}~~'


@MarkdownRenderer.register('mark')
def render_mark(renderer: MarkdownRenderer, node: Mark, context: RenderContext) -> str:
    return f'=={renderer.render_children(node.children, context)}=='


@MarkdownRenderer.register('insert')
def render_insert(renderer: MarkdownRenderer, node: Insert, context: RenderContext) -> str:
    return f'^^{renderer.render_children(node.children, context)}^^'


@MarkdownRenderer.register('superscript')
def render_superscript(renderer: MarkdownRenderer, node: Superscript, context: RenderContext) -> str:
    return f'^{renderer.render_script_children(node, "^", context)}^'


@MarkdownRenderer.register('subscript')
def render_subscript(renderer: MarkdownRenderer, node: Subscript, context: RenderContext) -> str:
    return f'~{renderer.render_script_children(node, "~", context)}~'


@MarkdownRenderer.register('ruby')
def render_ruby(renderer: MarkdownRenderer, node: Ruby, context: RenderContext) -> str:
    segments = ''.join(f'{segment["base"]}({segment["text"]})' for segment in node.segments)
    return f'[{segments}]'


@MarkdownRenderer.register('inlineSpoiler')
def render_inline_spoiler(renderer: MarkdownRenderer, node: InlineSpoiler, context: RenderContext) -> str:
    return f'>! {renderer.render_children(node.children, context)} !<'


@MarkdownRenderer.register('textDirective')
def render_text_directive(renderer: MarkdownRenderer, node: TextDirective, context: RenderContext) -> str:
    return (
        f':{node.name}'
        f'{renderer.render_directive_label(node, context)}'
        f'{renderer.render_directive_attributes(node.attributes)}'
    )


@MarkdownRenderer.register('leafDirective')
def render_leaf_directive(renderer: MarkdownRenderer, node: LeafDirective, context: RenderContext) -> str:
    return (
        f'::{node.name}'
        f'{renderer.render_directive_label(node, context)}'
        f'{renderer.render_directive_attributes(node.attributes)}'
        '\n\n'
    )


@MarkdownRenderer.register('containerDirective')
def render_container_directive(renderer: MarkdownRenderer, node: ContainerDirective, context: RenderContext) -> str:
    children = list(node.children)
    label = ''
    if children and isinstance(children[0], Paragraph) and children[0].data == {'directiveLabel': True}:
        label = renderer.render_directive_label(children.pop(0), context)

    body = renderer.render_children(children, context).rstrip('\n')
    head = f':::{node.name}{label}{renderer.render_directive_attributes(node.attributes)}'
    if body:
        return f'{head}\n{body}\n:::\n\n'
    return f'{head}\n:::\n\n'


@MarkdownRenderer.register('table')
def render_table(renderer: MarkdownRenderer, node: Table, context: RenderContext) -> str:
    if not node.children:
        return ''

    header = normalize_table_row(node.children[0], len(node.align))
    body = [normalize_table_row(row, len(node.align)) for row in node.children[1:]]
    lines = [
        '| ' + ' | '.join(renderer.render_table_cell_content(cell, context) for cell in header) + ' |',
        '| ' + ' | '.join(delimiter_for_align(align) for align in node.align) + ' |',
    ]
    lines.extend(
        '| ' + ' | '.join(renderer.render_table_cell_content(cell, context) for cell in row) + ' |' for row in body
    )
    return '\n'.join(lines) + '\n\n'


@MarkdownRenderer.register('tableRow')
def render_table_row(renderer: MarkdownRenderer, node: TableRow, context: RenderContext) -> str:
    cells = [cell for cell in node.children if isinstance(cell, TableCell)]
    return '| ' + ' | '.join(renderer.render_table_cell_content(cell, context) for cell in cells) + ' |\n'


@MarkdownRenderer.register('tableCell')
def render_table_cell(renderer: MarkdownRenderer, node: TableCell, context: RenderContext) -> str:
    return renderer.render_table_cell_content(node, context)


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


def quote_directive_attribute(value: str) -> str:
    if value and not re.search(r'[\s"\'=<>`{}]', value):
        return value
    return '"' + value.replace('\\', '\\\\').replace('"', '\\"') + '"'


@MarkdownRenderer.register('code')
def render_code(renderer: MarkdownRenderer, node: Code, context: RenderContext) -> str:
    longest_fence = max((len(match.group(0)) for match in re.finditer(r'`+', node.value)), default=2)
    fence = '`' * max(3, longest_fence + 1)
    info = node.lang or ''
    if node.meta:
        info = (info + ' ' + node.meta).strip()
    value = node.value if node.value.endswith('\n') else node.value + '\n'
    return f'{fence}{info}\n{value}{fence}\n\n'


@MarkdownRenderer.register('math')
def render_math(renderer: MarkdownRenderer, node: Math, context: RenderContext) -> str:
    value = node.value if node.value.endswith('\n') else node.value + '\n'
    return f'$$\n{value}$$\n\n'


@MarkdownRenderer.register('thematicBreak')
def render_thematic_break(renderer: MarkdownRenderer, node: ThematicBreak, context: RenderContext) -> str:
    return '---\n\n'


@MarkdownRenderer.register('html')
def render_html(renderer: MarkdownRenderer, node: Html, context: RenderContext) -> str:
    if node.value.endswith('\n'):
        return node.value.rstrip('\n') + '\n\n'
    return node.value


@MarkdownRenderer.register('text')
def render_text(renderer: MarkdownRenderer, node: Text, context: RenderContext) -> str:
    return renderer.escape_text(node.value)


@MarkdownRenderer.register('inlineCode')
def render_inline_code(renderer: MarkdownRenderer, node: InlineCode, context: RenderContext) -> str:
    longest_fence = max((len(match.group(0)) for match in re.finditer(r'`+', node.value)), default=0)
    fence = '`' * (longest_fence + 1)
    needs_padding = node.value.startswith(('`', ' ')) or node.value.endswith(('`', ' '))
    if needs_padding:
        return f'{fence} {node.value} {fence}'
    return f'{fence}{node.value}{fence}'


@MarkdownRenderer.register('inlineMath')
def render_inline_math(renderer: MarkdownRenderer, node: InlineMath, context: RenderContext) -> str:
    return f'${node.value}$'


@MarkdownRenderer.register('strong')
def render_strong(renderer: MarkdownRenderer, node: Strong, context: RenderContext) -> str:
    return f'**{renderer.render_children(node.children, context)}**'


@MarkdownRenderer.register('emphasis')
def render_emphasis(renderer: MarkdownRenderer, node: Emphasis, context: RenderContext) -> str:
    return f'*{renderer.render_children(node.children, context)}*'


@MarkdownRenderer.register('link')
def render_link(renderer: MarkdownRenderer, node: Link, context: RenderContext) -> str:
    title = f' "{renderer.escape_title(node.title)}"' if node.title else ''
    return f'[{renderer.render_children(node.children, context)}]({renderer.escape_destination(node.url)}{title})'


@MarkdownRenderer.register('image')
def render_image(renderer: MarkdownRenderer, node: Image, context: RenderContext) -> str:
    title = f' "{renderer.escape_title(node.title)}"' if node.title else ''
    return f'![{renderer.escape_text(node.alt)}]({renderer.escape_destination(node.url)}{title})'


@MarkdownRenderer.register('break')
def render_break(renderer: MarkdownRenderer, node: Break, context: RenderContext) -> str:
    return '  \n'


@MarkdownRenderer.register('footnoteReference')
def render_footnote_reference(renderer: MarkdownRenderer, node: FootnoteReference, context: RenderContext) -> str:
    return f'[^{renderer.escape_text(node.label or node.identifier)}]'


@MarkdownRenderer.register('footnoteDefinition')
def render_footnote_definition(renderer: MarkdownRenderer, node: FootnoteDefinition, context: RenderContext) -> str:
    label = renderer.escape_text(node.label or node.identifier)
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return f'[^{label}]:\n\n'

    lines = body.splitlines()
    return f'[^{label}]: {lines[0]}\n' + ''.join(f'  {line}\n' for line in lines[1:]) + '\n'
