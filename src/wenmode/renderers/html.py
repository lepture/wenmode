from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import quote, urlsplit

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
    Node,
    Paragraph,
    Root,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    TextDirective,
    ThematicBreak,
)

from .base import BaseRenderer, RenderContext

HtmlAttrValue = str | int | bool | None
SOFT_BREAK_SPACE_RE = re.compile(r'(?<! ) (?=\r?\n)')


@dataclass
class FootnoteRenderState:
    """Mutable render state used while rendering footnotes."""

    definitions: dict[str, FootnoteDefinition] = field(default_factory=dict)
    numbers: dict[str, int] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    reference_ids: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class HTMLRenderContext(RenderContext):
    """Render context for :class:`HTMLRenderer`."""

    footnotes: FootnoteRenderState = field(default_factory=FootnoteRenderState)
    root: Root | None = None


class DirectiveHtmlRenderer(Protocol):
    """Protocol for HTML directive renderers.

    Implementations are registered on :class:`HTMLRenderer` and are selected by
    ``node_type`` plus directive name.
    """

    node_type: str
    names: Iterable[str]

    def render(self, renderer: HTMLRenderer, node: Any, context: HTMLRenderContext) -> str:
        """Render a matched directive node to HTML."""
        pass


class HTMLRenderer(BaseRenderer):
    """Render Wenmode nodes as HTML.

    :param escape: Escape raw HTML nodes when ``True``.
    :param sanitize_urls: Drop unsafe URL schemes from links and images when
        ``True``.
    :param directives: Directive renderers to register at construction time.
    """

    name = 'html'
    allowed_url_schemes = frozenset({'http', 'https', 'irc', 'ircs', 'mailto', 'tel'})

    def __init__(
        self,
        escape: bool = True,
        sanitize_urls: bool = True,
        directives: Iterable[DirectiveHtmlRenderer] = (),
    ) -> None:
        super().__init__()
        self.escape_enabled = escape
        self.sanitize_urls = sanitize_urls
        self.directives: dict[tuple[str, str], DirectiveHtmlRenderer] = {}
        for directive in directives:
            self.register_directive_renderer(directive)

    def create_context(self, node: Node | None = None) -> HTMLRenderContext:
        """Create an HTML render context."""
        if isinstance(node, Root):
            definitions = node.footnote_definitions
            root = node
        else:
            definitions = None
            root = None
        context = HTMLRenderContext(
            footnotes=FootnoteRenderState(definitions=definitions or {}),
            root=root,
        )
        return context

    def register_directive_renderer(self, directive: DirectiveHtmlRenderer) -> None:
        """Register one directive renderer.

        :param directive: Directive renderer implementation.
        """
        for name in directive.names:
            self.directives[(directive.node_type, name)] = directive

    def render_list_item(self, item: Node, loose: bool, context: HTMLRenderContext) -> str:
        if not isinstance(item, ListItem):
            return self.render_node(item, context)
        if not item.children:
            return '<li></li>\n'
        if not loose:
            if isinstance(item.children[0], Paragraph):
                prefix = '<li>'
            else:
                prefix = '<li>\n'
            parts: list[str] = []
            for index, child in enumerate(item.children):
                if isinstance(child, Paragraph):
                    if index == 0:
                        marker = self.render_task_marker(item)
                    else:
                        marker = ''
                    parts.append(marker)
                    parts.append(self.render_children(child.children, context))
                    if index < len(item.children) - 1:
                        parts.append('\n')
                else:
                    if index == 0:
                        parts.append(self.render_task_marker(item))
                    parts.append(self.render_node(child, context))
            return prefix + ''.join(parts) + '</li>\n'
        return '<li>\n' + self.render_loose_list_item_children(item, context) + '</li>\n'

    def render_loose_list_item_children(self, item: ListItem, context: HTMLRenderContext) -> str:
        parts: list[str] = []
        for index, child in enumerate(item.children):
            if index == 0 and isinstance(child, Paragraph) and item.checked is not None:
                parts.append(
                    '<p>' + self.render_task_marker(item) + self.render_children(child.children, context) + '</p>\n'
                )
            else:
                if index == 0 and item.checked is not None:
                    parts.append(self.render_task_marker(item))
                parts.append(self.render_node(child, context))
        return ''.join(parts)

    def render_task_marker(self, item: ListItem) -> str:
        if item.checked is None:
            return ''
        if item.checked:
            return '<input checked="" disabled="" type="checkbox"> '
        return '<input disabled="" type="checkbox"> '

    def escape(self, value: str) -> str:
        """Escape raw HTML when renderer escaping is enabled."""
        if not self.escape_enabled:
            return value
        return self.escape_html(value)

    def escape_html(self, value: str) -> str:
        """Escape a string for HTML text or attribute output."""
        return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def render_attrs(self, attrs: Mapping[str, HtmlAttrValue]) -> str:
        """Render a mapping as HTML attributes.

        ``None`` and ``False`` values are omitted. ``True`` values render as
        boolean attributes.
        """
        rendered: list[str] = []
        for name, value in attrs.items():
            if value is None or value is False:
                continue
            if value is True:
                rendered.append(name)
            else:
                rendered.append(f'{name}="{self.escape_html(str(value))}"')
        if rendered:
            return ' ' + ' '.join(rendered)
        return ''

    def sanitize_url(self, value: str) -> str | None:
        """Return a URL if its scheme is allowed, otherwise ``None``."""
        if not self.sanitize_urls:
            return value

        normalized = ''.join(char for char in value.strip() if char > ' ')
        scheme = urlsplit(normalized).scheme.lower()
        if scheme and scheme not in self.allowed_url_schemes:
            return None
        return value

    def render_footnote_section(self, context: HTMLRenderContext) -> str:
        if not context.footnotes.order:
            return ''

        parts = [
            '<section data-footnotes class="footnotes">\n',
            '<h2 class="sr-only" id="footnote-label">Footnotes</h2>\n',
            '<ol>\n',
        ]
        for identifier in context.footnotes.order:
            definition = context.footnotes.definitions.get(identifier)
            if definition is None:
                continue
            parts.append(f'<li id="{self.escape_html(footnote_id(identifier))}">\n')
            parts.append(self.render_footnote_definition_content(definition, context))
            parts.append('</li>\n')
        parts.append('</ol>\n</section>\n')
        return ''.join(parts)

    def render_footnote_definition_content(self, definition: FootnoteDefinition, context: HTMLRenderContext) -> str:
        content = self.render_children(definition.children, context)
        backrefs = ''.join(
            f' <a href="#{self.escape_html(reference_id)}" data-footnote-backref '
            f'class="data-footnote-backref" aria-label="Back to content">&#8617;</a>'
            for reference_id in context.footnotes.reference_ids.get(definition.identifier, [])
        )
        if backrefs == '':
            return content
        if content.endswith('</p>\n'):
            return content[:-5] + backrefs + '</p>\n'
        return content + backrefs + '\n'

    def render_directive(
        self, node: TextDirective | LeafDirective | ContainerDirective, context: HTMLRenderContext
    ) -> str | None:
        directive = self.directives.get((node.type, node.name))
        if directive is None:
            return None
        return directive.render(self, node, context)

    def render_directive_or_children(
        self, node: TextDirective | LeafDirective | ContainerDirective, context: HTMLRenderContext
    ) -> str:
        rendered = self.render_directive(node, context)
        if rendered is not None:
            return rendered
        return self.render_children(node.children, context)


@HTMLRenderer.register('root')
def render_root(renderer: HTMLRenderer, node: Root, context: HTMLRenderContext) -> str:
    out = renderer.render_children(node.children, context)
    if node.footnote_definitions:
        out += renderer.render_footnote_section(context)
    return out


@HTMLRenderer.register('paragraph')
def render_paragraph(renderer: HTMLRenderer, node: Paragraph, context: HTMLRenderContext) -> str:
    return f'<p>{renderer.render_children(node.children, context)}</p>\n'


@HTMLRenderer.register('heading')
def render_heading(renderer: HTMLRenderer, node: Heading, context: HTMLRenderContext) -> str:
    attrs: dict[str, HtmlAttrValue] = {}
    if node.data:
        identifier = node.data.get('id')
    else:
        identifier = None
    if isinstance(identifier, str):
        attrs['id'] = identifier
    return f'<h{node.depth}{renderer.render_attrs(attrs)}>{renderer.render_children(node.children, context)}</h{node.depth}>\n'


@HTMLRenderer.register('blockquote')
def render_blockquote(renderer: HTMLRenderer, node: Blockquote, context: HTMLRenderContext) -> str:
    return '<blockquote>\n' + renderer.render_children(node.children, context) + '</blockquote>\n'


@HTMLRenderer.register('list')
def render_list(renderer: HTMLRenderer, node: List, context: HTMLRenderContext) -> str:
    if node.ordered:
        tag = 'ol'
    else:
        tag = 'ul'
    if node.ordered and node.start not in (None, 1):
        start = f' start="{node.start}"'
    else:
        start = ''
    return (
        f'<{tag}{start}>\n'
        + ''.join(renderer.render_list_item(child, node.spread, context) for child in node.children)
        + f'</{tag}>\n'
    )


@HTMLRenderer.register('listItem')
def render_list_item(renderer: HTMLRenderer, node: ListItem, context: HTMLRenderContext) -> str:
    return renderer.render_list_item(node, node.spread, context)


@HTMLRenderer.register('delete')
def render_delete(renderer: HTMLRenderer, node: Delete, context: HTMLRenderContext) -> str:
    return f'<del>{renderer.render_children(node.children, context)}</del>'


@HTMLRenderer.register('containerDirective')
@HTMLRenderer.register('leafDirective')
@HTMLRenderer.register('textDirective')
def render_directive_node(
    renderer: HTMLRenderer, node: TextDirective | LeafDirective | ContainerDirective, context: HTMLRenderContext
) -> str:
    return renderer.render_directive_or_children(node, context)


@HTMLRenderer.register('table')
def render_table(renderer: HTMLRenderer, node: Table, context: HTMLRenderContext) -> str:
    if not node.children:
        return '<table>\n</table>\n'

    header = node.children[0]
    body = node.children[1:]
    output = ['<table>\n<thead>\n', render_table_row(renderer, header, 'th', node.align, context), '</thead>\n']
    if body:
        output.append('<tbody>\n')
        output.extend(render_table_row(renderer, row, 'td', node.align, context) for row in body)
        output.append('</tbody>\n')
    output.append('</table>\n')
    return ''.join(output)


@HTMLRenderer.register('tableRow')
def render_table_row_node(renderer: HTMLRenderer, node: TableRow, context: HTMLRenderContext) -> str:
    return render_table_row(renderer, node, 'td', [], context)


@HTMLRenderer.register('tableCell')
def render_table_cell_node(renderer: HTMLRenderer, node: TableCell, context: HTMLRenderContext) -> str:
    return f'<td>{renderer.render_children(node.children, context)}</td>'


def render_table_row(
    renderer: HTMLRenderer, row: Node, tag: str, align: list[str | None], context: HTMLRenderContext
) -> str:
    if not isinstance(row, TableRow):
        return renderer.render_node(row, context)
    output = ['<tr>\n']
    for index, cell in enumerate(row.children):
        if not isinstance(cell, TableCell):
            output.append(renderer.render_node(cell, context))
            continue
        if index < len(align) and align[index] is not None:
            attrs = {'align': align[index]}
        else:
            attrs = {}
        output.append(
            f'<{tag}{renderer.render_attrs(attrs)}>{renderer.render_children(cell.children, context)}</{tag}>\n'
        )
    output.append('</tr>\n')
    return ''.join(output)


@HTMLRenderer.register('code')
def render_code(renderer: HTMLRenderer, node: Code, context: HTMLRenderContext) -> str:
    if node.lang:
        lang = f' class="language-{renderer.escape_html(node.lang)}"'
    else:
        lang = ''
    return f'<pre><code{lang}>{renderer.escape_html(node.value)}</code></pre>\n'


@HTMLRenderer.register('thematicBreak')
def render_thematic_break(renderer: HTMLRenderer, node: ThematicBreak, context: HTMLRenderContext) -> str:
    return '<hr />\n'


@HTMLRenderer.register('html')
def render_html(renderer: HTMLRenderer, node: Html, context: HTMLRenderContext) -> str:
    if node.data and node.data.get('escaped'):
        return node.value
    return renderer.escape(node.value)


@HTMLRenderer.register('text')
def render_text(renderer: HTMLRenderer, node: Text, context: HTMLRenderContext) -> str:
    return renderer.escape_html(SOFT_BREAK_SPACE_RE.sub('', node.value))


@HTMLRenderer.register('inlineCode')
def render_inline_code(renderer: HTMLRenderer, node: InlineCode, context: HTMLRenderContext) -> str:
    return f'<code>{renderer.escape_html(node.value)}</code>'


@HTMLRenderer.register('strong')
def render_strong(renderer: HTMLRenderer, node: Strong, context: HTMLRenderContext) -> str:
    return f'<strong>{renderer.render_children(node.children, context)}</strong>'


@HTMLRenderer.register('emphasis')
def render_emphasis(renderer: HTMLRenderer, node: Emphasis, context: HTMLRenderContext) -> str:
    return f'<em>{renderer.render_children(node.children, context)}</em>'


@HTMLRenderer.register('link')
def render_link(renderer: HTMLRenderer, node: Link, context: HTMLRenderContext) -> str:
    attrs: dict[str, HtmlAttrValue] = {}
    href = renderer.sanitize_url(node.url)
    if href is not None:
        attrs['href'] = href
    if node.title:
        attrs['title'] = node.title
    return f'<a{renderer.render_attrs(attrs)}>{renderer.render_children(node.children, context)}</a>'


@HTMLRenderer.register('image')
def render_image(renderer: HTMLRenderer, node: Image, context: HTMLRenderContext) -> str:
    attrs: dict[str, HtmlAttrValue] = {}
    src = renderer.sanitize_url(node.url)
    if src is not None:
        attrs['src'] = src
    attrs['alt'] = node.alt
    if node.title:
        attrs['title'] = node.title
    return f'<img{renderer.render_attrs(attrs)} />'


@HTMLRenderer.register('break')
def render_break(renderer: HTMLRenderer, node: Break, context: HTMLRenderContext) -> str:
    return '<br />\n'


@HTMLRenderer.register('footnoteReference')
def render_footnote_reference(renderer: HTMLRenderer, node: FootnoteReference, context: HTMLRenderContext) -> str:
    footnotes = context.footnotes
    if node.identifier not in footnotes.definitions:
        label = renderer.escape_html(node.label or node.identifier)
        return f'[^{label}]'

    if node.identifier not in footnotes.numbers:
        footnotes.numbers[node.identifier] = len(footnotes.order) + 1
        footnotes.order.append(node.identifier)

    number = footnotes.numbers[node.identifier]
    references = footnotes.reference_ids.setdefault(node.identifier, [])
    base_reference_id = footnote_reference_id(node.identifier)
    if not references:
        reference_id = base_reference_id
    else:
        reference_id = f'{base_reference_id}-{len(references) + 1}'
    references.append(reference_id)
    href = footnote_id(node.identifier)
    return (
        f'<sup><a href="#{renderer.escape_html(href)}" id="{renderer.escape_html(reference_id)}" '
        f'data-footnote-ref aria-describedby="footnote-label">{number}</a></sup>'
    )


@HTMLRenderer.register('footnoteDefinition')
def render_footnote_definition(renderer: HTMLRenderer, node: FootnoteDefinition, context: HTMLRenderContext) -> str:
    return ''


def footnote_id(identifier: str) -> str:
    return 'user-content-fn-' + quote(identifier, safe='-_.~')


def footnote_reference_id(identifier: str) -> str:
    return 'user-content-fnref-' + quote(identifier, safe='-_.~')
