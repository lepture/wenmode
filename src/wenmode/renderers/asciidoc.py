from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import cast

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
    Root,
    Strong,
    Table,
    Text,
    TextDirective,
    ThematicBreak,
)

from ._shared import footnote_label, render_table_cell_content, table_rows
from .base import BaseRenderer, RenderContext

ESCAPABLE_TEXT_RE = re.compile(r'([\\*_`#\[\]|])')


@dataclass
class AsciiDocRenderContext(RenderContext):
    """Render context for :class:`AsciiDocRenderer`."""

    root: Root | None = None
    list_stack: list[bool] = field(default_factory=list)


class AsciiDocRenderer(BaseRenderer):
    """Render Wenmode nodes as normalized AsciiDoc.

    The renderer is a best-effort serializer for Wenmode's core AST nodes. It is
    not source preserving and does not install handlers for built-in plugin
    nodes.
    """

    name = 'asciidoc'

    def create_context(self, node: Node | None = None) -> AsciiDocRenderContext:
        """Create an AsciiDoc render context."""
        if isinstance(node, Root):
            root = node
        else:
            root = None
        return AsciiDocRenderContext(root=root)

    def escape_text(self, value: str) -> str:
        """Escape common AsciiDoc inline punctuation in plain text."""
        return ESCAPABLE_TEXT_RE.sub(r'\\\1', value)

    def escape_link_target(self, value: str) -> str:
        """Escape a link or image target."""
        return value.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ')

    def escape_attribute_value(self, value: str) -> str:
        """Escape text inside an AsciiDoc macro attribute."""
        return value.replace('\r\n', ' ').replace('\r', ' ').replace('\n', ' ').replace('"', '\\"')


@AsciiDocRenderer.register('root')
def render_root(renderer: AsciiDocRenderer, node: Root, context: AsciiDocRenderContext) -> str:
    output = renderer.render_children(node.children, context).rstrip()
    if output:
        return output + '\n'
    return ''


@AsciiDocRenderer.register('paragraph')
def render_paragraph(renderer: AsciiDocRenderer, node: Paragraph, context: AsciiDocRenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n\n'


@AsciiDocRenderer.register('heading')
def render_heading(renderer: AsciiDocRenderer, node: Heading, context: AsciiDocRenderContext) -> str:
    depth = min(max(node.depth, 1), 6)
    title = renderer.render_children(node.children, context).strip()
    return f'{"=" * depth} {title}\n\n'


@AsciiDocRenderer.register('blockquote')
def render_blockquote(renderer: AsciiDocRenderer, node: Blockquote, context: AsciiDocRenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return '____\n____\n\n'
    return f'____\n{body}\n____\n\n'


@AsciiDocRenderer.register('list')
def render_list(renderer: AsciiDocRenderer, node: List, context: AsciiDocRenderContext) -> str:
    context.list_stack.append(node.ordered)
    try:
        parts: list[str] = []
        for child in node.children:
            if isinstance(child, ListItem):
                parts.append(render_list_item(renderer, child, context))
            else:  # pragma: no cover
                parts.append(renderer.render_node(child, context).rstrip('\n'))
        if node.spread:
            separator = '\n\n'
        else:
            separator = '\n'
        return separator.join(parts) + '\n\n'
    finally:
        context.list_stack.pop()


def render_list_item(renderer: AsciiDocRenderer, item: ListItem, context: AsciiDocRenderContext) -> str:
    marker = render_list_marker(context)
    if item.checked is True:
        marker += ' [x]'
    elif item.checked is False:
        marker += ' [ ]'

    if not item.children:
        return marker

    children = list(item.children)
    parts: list[str] = []
    first = children.pop(0)
    if isinstance(first, Paragraph):
        parts.append(marker + ' ' + renderer.render_children(first.children, context).strip())
    else:
        parts.append(marker)
        rendered = renderer.render_node(first, context).rstrip('\n')
        if rendered:
            parts.append('+\n' + rendered)

    for child in children:
        rendered = renderer.render_node(child, context).rstrip('\n')
        if not rendered:
            continue
        if isinstance(child, List):
            parts.append(rendered)
        else:
            parts.append('+\n' + rendered)
    return '\n'.join(parts)


def render_list_marker(context: AsciiDocRenderContext) -> str:
    ordered = context.list_stack[-1] if context.list_stack else False
    marker = '.' if ordered else '*'
    return marker * max(len(context.list_stack), 1)


@AsciiDocRenderer.register('delete')
def render_delete(renderer: AsciiDocRenderer, node: Delete, context: AsciiDocRenderContext) -> str:
    return f'[.line-through]#{renderer.render_children(node.children, context)}#'


@AsciiDocRenderer.register('textDirective')
def render_text_directive(renderer: AsciiDocRenderer, node: TextDirective, context: AsciiDocRenderContext) -> str:
    return renderer.render_children(node.children, context)


@AsciiDocRenderer.register('leafDirective')
def render_leaf_directive(renderer: AsciiDocRenderer, node: LeafDirective, context: AsciiDocRenderContext) -> str:
    return renderer.render_children(node.children, context) + '\n\n'


@AsciiDocRenderer.register('containerDirective')
def render_container_directive(
    renderer: AsciiDocRenderer, node: ContainerDirective, context: AsciiDocRenderContext
) -> str:
    children = list(node.children)
    title = ''
    if children and isinstance(children[0], Paragraph) and children[0].data == {'directiveLabel': True}:
        label = cast(Paragraph, children.pop(0))
        title = '.' + renderer.render_children(label.children, context).strip() + '\n'
    body = renderer.render_children(children, context).rstrip('\n')
    if body:
        return f'{title}--\n{body}\n--\n\n'
    if title:
        return title + '\n'
    return ''


@AsciiDocRenderer.register('literalDirective')
def render_literal_directive(renderer: AsciiDocRenderer, node: LiteralDirective, context: AsciiDocRenderContext) -> str:
    if node.name in {'code-block', 'sourcecode'}:
        return render_source_block(node.value, node.argument)
    return render_listing_block(node.value)


@AsciiDocRenderer.register('table')
def render_table(renderer: AsciiDocRenderer, node: Table, context: AsciiDocRenderContext) -> str:
    rows = table_rows(node)
    if not rows:
        return ''

    attributes = ['options="header"']
    columns = render_table_columns(node.align)
    if columns:
        attributes.insert(0, f'cols="{columns}"')
    lines = ['[' + ','.join(attributes) + ']']
    lines.append('|===')
    for row in rows:
        cells = [render_table_cell_content(renderer, cell, context) for cell in row]
        lines.append('| ' + ' | '.join(cells))
    lines.append('|===')
    return '\n'.join(lines) + '\n\n'


def render_table_columns(align: list[str | None]) -> str:
    markers = []
    for value in align:
        if value == 'left':
            markers.append('<')
        elif value == 'center':
            markers.append('^')
        elif value == 'right':
            markers.append('>')
        else:
            markers.append('')
    return ','.join(markers).strip(',')


@AsciiDocRenderer.register('code')
def render_code(renderer: AsciiDocRenderer, node: Code, context: AsciiDocRenderContext) -> str:
    return render_source_block(node.value, node.lang)


def render_source_block(value: str, language: str | None) -> str:
    head = f'[source,{language}]\n' if language else ''
    return head + render_listing_block(value)


def render_listing_block(value: str) -> str:
    body = value.rstrip('\n')
    delimiter = listing_delimiter(body)
    if body:
        return f'{delimiter}\n{body}\n{delimiter}\n\n'
    return f'{delimiter}\n{delimiter}\n\n'


def listing_delimiter(value: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r'^-+', value, re.MULTILINE)), default=0)
    return '-' * max(4, longest + 1)


@AsciiDocRenderer.register('thematicBreak')
def render_thematic_break(renderer: AsciiDocRenderer, node: ThematicBreak, context: AsciiDocRenderContext) -> str:
    return "'''\n\n"


@AsciiDocRenderer.register('html')
def render_html(renderer: AsciiDocRenderer, node: Html, context: AsciiDocRenderContext) -> str:
    value = node.value.rstrip('\n')
    if '\n' not in value:
        return f'pass:[{value}]'
    if value:
        return f'++++\n{value}\n++++\n\n'
    return ''


@AsciiDocRenderer.register('text')
def render_text(renderer: AsciiDocRenderer, node: Text, context: AsciiDocRenderContext) -> str:
    return renderer.escape_text(node.value)


@AsciiDocRenderer.register('inlineCode')
def render_inline_code(renderer: AsciiDocRenderer, node: InlineCode, context: AsciiDocRenderContext) -> str:
    delimiter = inline_passthrough_delimiter(node.value)
    return f'{delimiter}{node.value}{delimiter}'


def inline_passthrough_delimiter(value: str) -> str:
    longest = max((len(match.group(0)) for match in re.finditer(r'\++', value)), default=0)
    return '+' * max(1, longest + 1)


@AsciiDocRenderer.register('strong')
def render_strong(renderer: AsciiDocRenderer, node: Strong, context: AsciiDocRenderContext) -> str:
    return f'*{renderer.render_children(node.children, context)}*'


@AsciiDocRenderer.register('emphasis')
def render_emphasis(renderer: AsciiDocRenderer, node: Emphasis, context: AsciiDocRenderContext) -> str:
    return f'_{renderer.render_children(node.children, context)}_'


@AsciiDocRenderer.register('link')
def render_link(renderer: AsciiDocRenderer, node: Link, context: AsciiDocRenderContext) -> str:
    label = renderer.escape_attribute_value(plain_text(node.children) or node.url)
    return f'link:{renderer.escape_link_target(node.url)}[{label}]'


@AsciiDocRenderer.register('image')
def render_image(renderer: AsciiDocRenderer, node: Image, context: AsciiDocRenderContext) -> str:
    attrs = [renderer.escape_attribute_value(node.alt)]
    if node.title:
        attrs.append(f'title="{renderer.escape_attribute_value(node.title)}"')
    return f'image:{renderer.escape_link_target(node.url)}[{",".join(attrs)}]'


@AsciiDocRenderer.register('break')
def render_break(renderer: AsciiDocRenderer, node: Break, context: AsciiDocRenderContext) -> str:
    return ' +\n'


@AsciiDocRenderer.register('footnoteReference')
def render_footnote_reference(
    renderer: AsciiDocRenderer, node: FootnoteReference, context: AsciiDocRenderContext
) -> str:
    label = footnote_label(node.label or node.identifier)
    definitions = context.root.footnote_definitions if context.root is not None else None
    definition = definitions.get(node.identifier) if definitions is not None else None
    if definition is None:
        return f'footnote:[{renderer.escape_attribute_value(node.label or node.identifier)}]'
    body = renderer.render_children(definition.children, context).replace('\n', ' ').strip()
    return f'footnote:{label}[{renderer.escape_attribute_value(body)}]'


@AsciiDocRenderer.register('footnoteDefinition')
def render_footnote_definition(
    renderer: AsciiDocRenderer, node: FootnoteDefinition, context: AsciiDocRenderContext
) -> str:
    return ''
