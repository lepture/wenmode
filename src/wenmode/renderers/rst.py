from __future__ import annotations

import re
from dataclasses import dataclass, field

from wenmode.ast import plain_text
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
    LeafDirective,
    Link,
    List,
    ListItem,
    LiteralDirective,
    Node,
    Paragraph,
    Parent,
    Root,
    Strong,
    Table,
    Text,
    TextDirective,
    ThematicBreak,
)

from ._shared import footnote_label, render_table_cell_content, table_rows
from .base import BaseRenderer, RenderContext

ESCAPABLE_TEXT_RE = re.compile(r'([\\`*|])')


@dataclass
class ImageReference:
    """Deferred reStructuredText image substitution."""

    name: str
    node: Image


@dataclass
class RSTRenderContext(RenderContext):
    """Render context for :class:`RSTRenderer`."""

    root: Root | None = None
    body_rendered: bool = False
    image_references: list[ImageReference] = field(default_factory=list)


class RSTRenderer(BaseRenderer):
    """Render Wenmode nodes as reStructuredText."""

    name = 'rst'
    heading_markers = ('=', '-', '~', '^', '"', '#')

    def create_context(self, node: Node | None = None) -> RSTRenderContext:
        """Create a reStructuredText render context."""
        if isinstance(node, Root):
            root = node
        else:
            root = None
        return RSTRenderContext(root=root)

    def escape_text(self, value: str) -> str:
        """Escape reStructuredText punctuation in plain text."""
        return ESCAPABLE_TEXT_RE.sub(r'\\\1', value)

    def escape_inline_literal(self, value: str) -> str:
        """Escape text inside an inline literal."""
        return value

    def escape_interpreted_text(self, value: str) -> str:
        """Escape text inside a reStructuredText interpreted text role."""
        escaped = value.replace('`', '\\`')
        if escaped.startswith(' '):
            escaped = '\\' + escaped
        if escaped.endswith(' '):
            escaped = escaped[:-1] + '\\ '
        return escaped

    def escape_link_label(self, value: str) -> str:
        """Escape text inside a reStructuredText hyperlink label."""
        return self.escape_text(value.replace('\n', ' ')).replace('<', '\\<').replace('>', '\\>')

    def escape_link_target(self, value: str) -> str:
        """Escape a link or image target."""
        return value.replace('\n', ' ').replace('`', '\\`').replace('>', '\\>')

    def escape_directive_option(self, value: str) -> str:
        """Escape text inside a one-line reStructuredText directive option."""
        return value.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

    def render_image_definition(self, reference: ImageReference) -> str:
        node = reference.node
        lines = [f'.. |{reference.name}| image:: {self.escape_link_target(node.url)}']
        if node.alt:
            lines.append(f'   :alt: {self.escape_directive_option(node.alt)}')
        if node.title:
            lines.append(f'   :title: {self.escape_directive_option(node.title)}')
        return '\n'.join(lines) + '\n\n'


@RSTRenderer.register('root')
def render_root(renderer: RSTRenderer, node: Root, context: RSTRenderContext) -> str:
    output = renderer.render_children(node.children, context).rstrip()
    context.body_rendered = bool(output)
    if output:
        return output + '\n'
    return ''


@RSTRenderer.register('root:post')
def render_root_image_references(renderer: RSTRenderer, node: Root, context: RSTRenderContext) -> str:
    images = ''.join(renderer.render_image_definition(reference) for reference in context.image_references).rstrip()
    if images:
        if context.body_rendered:
            return '\n' + images + '\n'
        return images + '\n'
    return ''


@RSTRenderer.register('paragraph')
def render_paragraph(renderer: RSTRenderer, node: Paragraph, context: RSTRenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n\n'


@RSTRenderer.register('heading')
def render_heading(renderer: RSTRenderer, node: Heading, context: RSTRenderContext) -> str:
    title = renderer.render_children(node.children, context).strip()
    marker = renderer.heading_markers[min(max(node.depth, 1), len(renderer.heading_markers)) - 1]
    return f'{title}\n{marker * max(len(title), 1)}\n\n'


@RSTRenderer.register('blockquote')
def render_blockquote(renderer: RSTRenderer, node: Blockquote, context: RSTRenderContext) -> str:
    return render_indented_block(renderer, node, context)


@RSTRenderer.register('list')
def render_list(renderer: RSTRenderer, node: List, context: RSTRenderContext) -> str:
    parts: list[str] = []
    start = node.start or 1
    if node.spread:
        separator = '\n\n'
    else:
        separator = '\n'

    for index, child in enumerate(node.children):
        if not isinstance(child, ListItem):  # pragma: no cover
            parts.append(renderer.render_node(child, context).rstrip('\n'))
            continue
        if node.ordered and node.start not in (None, 1):
            marker = f'{start + index}. '
        elif node.ordered:
            marker = '#. '
        else:
            marker = '- '
        parts.append(render_list_item(renderer, child, marker, context))

    return separator.join(parts) + '\n\n'


def render_list_item(renderer: RSTRenderer, item: ListItem, marker: str, context: RSTRenderContext) -> str:
    if item.checked is not None:
        if item.checked:
            marker += '[x] '
        else:
            marker += '[ ] '
    if not item.children:
        return marker.rstrip()

    body = renderer.render_children(item.children, context).rstrip('\n')
    lines = body.splitlines() or ['']
    indent = ' ' * len(marker)
    parts = [marker + lines[0]]
    for line in lines[1:]:
        if line:
            parts.append(indent + line)
        else:
            parts.append('')
    return '\n'.join(parts)


@RSTRenderer.register('delete')
def render_delete(renderer: RSTRenderer, node: Delete, context: RSTRenderContext) -> str:
    return renderer.render_children(node.children, context)


@RSTRenderer.register('textDirective')
def render_text_directive(renderer: RSTRenderer, node: TextDirective, context: RSTRenderContext) -> str:
    content = render_directive_argument(renderer, node, context)
    return f':{node.name}:`{content}`'


@RSTRenderer.register('leafDirective')
def render_leaf_directive(renderer: RSTRenderer, node: LeafDirective, context: RSTRenderContext) -> str:
    argument = render_directive_argument(renderer, node, context)
    head = f'.. {node.name}::'
    if argument:
        head += f' {argument}'
    options = render_directive_options(node.attributes)
    if options:
        return '\n'.join([head, *options]) + '\n\n'
    return head + '\n\n'


@RSTRenderer.register('containerDirective')
def render_container_directive(renderer: RSTRenderer, node: ContainerDirective, context: RSTRenderContext) -> str:
    children = list(node.children)
    argument = ''
    if children and isinstance(children[0], Paragraph) and children[0].data == {'directiveLabel': True}:
        label = children.pop(0)
        argument = render_directive_argument(renderer, label, context)

    head = f'.. {node.name}::'
    if argument:
        head += f' {argument}'
    options = render_directive_options(node.attributes)
    body = renderer.render_children(children, context).rstrip('\n')

    if not body:
        if options:
            return '\n'.join([head, *options]) + '\n\n'
        return head + '\n\n'

    lines = [head, *options, '', indent_block(body, '   ')]
    return '\n'.join(lines) + '\n\n'


@RSTRenderer.register('literalDirective')
def render_literal_directive(renderer: RSTRenderer, node: LiteralDirective, context: RSTRenderContext) -> str:
    head = f'.. {node.name}::'
    if node.argument:
        head += f' {node.argument}'
    options = render_directive_options(node.attributes)
    body = node.value.rstrip('\n')

    if not body:
        if options:
            return '\n'.join([head, *options]) + '\n\n'
        return head + '\n\n'

    lines = [head, *options, '', indent_block(body, '   ')]
    return '\n'.join(lines) + '\n\n'


def render_directive_argument(renderer: RSTRenderer, node: Node, context: RSTRenderContext) -> str:
    """Render a directive argument from a directive or label node."""
    children = getattr(node, 'children', None)
    if not isinstance(children, list):
        return ''
    return renderer.render_children(children, context).strip()


def render_directive_options(attributes: dict[str, str] | None) -> list[str]:
    if not attributes:
        return []

    options: list[str] = []
    for key, value in attributes.items():
        if key == 'id':
            option_name = 'name'
        else:
            option_name = key
        if key == 'class':
            option_name = 'class'
        if value == '':
            options.append(f'   :{option_name}:')
        else:
            options.append(f'   :{option_name}: {value}')
    return options


@RSTRenderer.register('table')
def render_table(renderer: RSTRenderer, node: Table, context: RSTRenderContext) -> str:
    rows = table_rows(node)
    if not rows:
        return ''

    rendered_rows = [[render_table_cell_content(renderer, cell, context) for cell in row] for row in rows]
    column_count = max((len(row) for row in rendered_rows), default=0)
    if column_count == 0:
        return ''

    for row in rendered_rows:
        row.extend('' for _ in range(column_count - len(row)))
    widths = [max(3, *(len(row[index]) for row in rendered_rows)) for index in range(column_count)]
    delimiter = render_table_delimiter(widths)
    lines = [delimiter, render_table_line(rendered_rows[0], widths), delimiter]
    lines.extend(render_table_line(row, widths) for row in rendered_rows[1:])
    lines.append(delimiter)
    return '\n'.join(lines) + '\n\n'


@RSTRenderer.register('code')
def render_code(renderer: RSTRenderer, node: Code, context: RSTRenderContext) -> str:
    if node.value.endswith('\n'):
        value = node.value
    else:
        value = node.value + '\n'
    body = indent_block(value.rstrip('\n'), '   ')
    if node.lang:
        return f'.. code-block:: {node.lang}\n\n{body}\n\n'
    return f'::\n\n{body}\n\n'


@RSTRenderer.register('thematicBreak')
def render_thematic_break(renderer: RSTRenderer, node: ThematicBreak, context: RSTRenderContext) -> str:
    return '----\n\n'


@RSTRenderer.register('html')
def render_html(renderer: RSTRenderer, node: Html, context: RSTRenderContext) -> str:
    value = node.value.rstrip('\n')
    if '\n' not in node.value:
        return node.value
    return '.. raw:: html\n\n' + indent_block(value, '   ') + '\n\n'


@RSTRenderer.register('text')
def render_text(renderer: RSTRenderer, node: Text, context: RSTRenderContext) -> str:
    return renderer.escape_text(node.value)


@RSTRenderer.register('inlineCode')
def render_inline_code(renderer: RSTRenderer, node: InlineCode, context: RSTRenderContext) -> str:
    if '`' in node.value:
        return f':literal:`{renderer.escape_interpreted_text(node.value)}`'
    return f'``{renderer.escape_inline_literal(node.value)}``'


@RSTRenderer.register('strong')
def render_strong(renderer: RSTRenderer, node: Strong, context: RSTRenderContext) -> str:
    return f'**{renderer.render_children(node.children, context)}**'


@RSTRenderer.register('emphasis')
def render_emphasis(renderer: RSTRenderer, node: Emphasis, context: RSTRenderContext) -> str:
    return f'*{renderer.render_children(node.children, context)}*'


@RSTRenderer.register('link')
def render_link(renderer: RSTRenderer, node: Link, context: RSTRenderContext) -> str:
    label = renderer.escape_link_label(plain_text(node.children) or node.url)
    return f'`{label} <{renderer.escape_link_target(node.url)}>`__'


@RSTRenderer.register('image')
def render_image(renderer: RSTRenderer, node: Image, context: RSTRenderContext) -> str:
    if context.root is None:  # pragma: no cover
        lines = [f'.. image:: {renderer.escape_link_target(node.url)}']
        if node.alt:
            lines.append(f'   :alt: {node.alt}')
        if node.title:
            lines.append(f'   :title: {node.title}')
        return '\n'.join(lines) + '\n\n'

    name = f'image-{len(context.image_references) + 1}'
    context.image_references.append(ImageReference(name=name, node=node))
    return f'|{name}|'


@RSTRenderer.register('break')
def render_break(renderer: RSTRenderer, node: Break, context: RSTRenderContext) -> str:
    return '\n'


@RSTRenderer.register('footnoteReference')
def render_footnote_reference(renderer: RSTRenderer, node: FootnoteReference, context: RSTRenderContext) -> str:
    return f'[#{footnote_label(node.label or node.identifier)}]_'


@RSTRenderer.register('footnoteDefinition')
def render_footnote_definition(renderer: RSTRenderer, node: FootnoteDefinition, context: RSTRenderContext) -> str:
    label = footnote_label(node.label or node.identifier)
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return f'.. [#{label}]\n\n'

    lines = body.splitlines()
    continuation_lines: list[str] = []
    for line in lines[1:]:
        if line:
            continuation_lines.append(f'   {line}\n')
        else:
            continuation_lines.append('\n')
    return f'.. [#{label}] {lines[0]}\n' + ''.join(continuation_lines) + '\n'


def indent_block(value: str, prefix: str) -> str:
    lines: list[str] = []
    for line in value.splitlines():
        if line:
            lines.append(prefix + line)
        else:
            lines.append('')
    return '\n'.join(lines)


def render_indented_block(renderer: RSTRenderer, node: Parent, context: RSTRenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return ''
    return indent_block(body, '   ') + '\n\n'


def render_table_delimiter(widths: list[int]) -> str:
    return '  '.join('=' * width for width in widths)


def render_table_line(cells: list[str], widths: list[int]) -> str:
    return '  '.join(cell.ljust(widths[index]) for index, cell in enumerate(cells)).rstrip()
