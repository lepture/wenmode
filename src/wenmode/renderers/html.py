from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol, cast
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
    LiteralDirective,
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
HTML_ATTR_NAME_RE = re.compile(r'^[A-Za-z_:][A-Za-z0-9_.:-]*$')


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
    :param sanitize_attrs: Drop event handler and style attribute names when
        ``True``.
    :param directives: Directive renderers to register at construction time.
    """

    name = 'html'
    allowed_url_schemes = frozenset({'http', 'https', 'irc', 'ircs', 'mailto', 'tel'})

    def __init__(
        self,
        escape: bool = True,
        sanitize_urls: bool = True,
        sanitize_attrs: bool = True,
        directives: Iterable[DirectiveHtmlRenderer] = (),
    ) -> None:
        super().__init__()
        self.escape_enabled = escape
        self.sanitize_urls = sanitize_urls
        self.sanitize_attrs = sanitize_attrs
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

    def render_unknown(self, node: Node, context: RenderContext) -> str:
        """Render an unknown node without allowing implicit HTML markup."""
        children = getattr(node, 'children', None)
        if isinstance(children, list):
            return self.render_children(cast(list[Node], children), context)

        value = getattr(node, 'value', None)
        if isinstance(value, str):
            return self.escape_html(value)

        return ''

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
            if self.sanitize_attrs and not self.is_safe_attr_name(name):
                continue
            if value is None or value is False:
                continue
            if value is True:
                rendered.append(name)
            else:
                rendered.append(f'{name}="{self.escape_html(str(value))}"')
        if rendered:
            return ' ' + ' '.join(rendered)
        return ''

    def is_safe_attr_name(self, name: str) -> bool:
        """Return whether an attribute name is safe for generated HTML."""
        if HTML_ATTR_NAME_RE.match(name) is None:
            return False
        lowered = name.lower()
        return not lowered.startswith('on') and lowered != 'style'

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
        self, node: TextDirective | LeafDirective | ContainerDirective | LiteralDirective, context: HTMLRenderContext
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
    return renderer.render_children(node.children, context)


@HTMLRenderer.register('root:post')
def render_root_footnotes(renderer: HTMLRenderer, node: Root, context: HTMLRenderContext) -> str:
    if node.footnote_definitions:
        return renderer.render_footnote_section(context)
    return ''


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
        + ''.join(render_list_item(renderer, cast(ListItem, child), node.spread, context) for child in node.children)
        + f'</{tag}>\n'
    )


def render_list_item(renderer: HTMLRenderer, item: ListItem, loose: bool, context: HTMLRenderContext) -> str:
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
                    marker = render_task_marker(item)
                else:
                    marker = ''
                parts.append(marker)
                parts.append(renderer.render_children(child.children, context))
                if index < len(item.children) - 1:
                    parts.append('\n')
            else:
                if index == 0:
                    parts.append(render_task_marker(item))
                parts.append(renderer.render_node(child, context))
        return prefix + ''.join(parts) + '</li>\n'
    return '<li>\n' + render_loose_list_item_children(renderer, item, context) + '</li>\n'


def render_loose_list_item_children(renderer: HTMLRenderer, item: ListItem, context: HTMLRenderContext) -> str:
    parts: list[str] = []
    for index, child in enumerate(item.children):
        if index == 0 and isinstance(child, Paragraph) and item.checked is not None:
            parts.append(
                '<p>' + render_task_marker(item) + renderer.render_children(child.children, context) + '</p>\n'
            )
        else:
            if index == 0 and item.checked is not None:
                parts.append(render_task_marker(item))
            parts.append(renderer.render_node(child, context))
    return ''.join(parts)


def render_task_marker(item: ListItem) -> str:
    if item.checked is None:
        return ''
    if item.checked:
        return '<input checked="" disabled="" type="checkbox"> '
    return '<input disabled="" type="checkbox"> '


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


@HTMLRenderer.register('literalDirective')
def render_literal_directive(renderer: HTMLRenderer, node: LiteralDirective, context: HTMLRenderContext) -> str:
    rendered = renderer.render_directive(node, context)
    if rendered is not None:
        return rendered
    if node.name == 'code-block':
        return renderer.render_node(Code(value=node.value, lang=node.argument), context)
    return renderer.escape_html(node.value)


@HTMLRenderer.register('table')
def render_table(renderer: HTMLRenderer, node: Table, context: HTMLRenderContext) -> str:
    if not node.children:  # pragma: no cover
        return '<table>\n</table>\n'

    header = node.children[0]
    body = node.children[1:]
    output = (
        '<table>\n<thead>\n'
        + render_table_row(renderer, cast(TableRow, header), 'th', node.align, context)
        + '</thead>\n'
    )
    if body:
        output += '<tbody>\n'
        for row in body:
            output += render_table_row(renderer, cast(TableRow, row), 'td', node.align, context)
        output += '</tbody>\n'
    output += '</table>\n'
    return output


def render_table_row(
    renderer: HTMLRenderer, row: TableRow, tag: str, align: list[str | None], context: HTMLRenderContext
) -> str:
    output = '<tr>\n'
    for index, cell in enumerate(row.children):
        if not isinstance(cell, TableCell):  # pragma: no cover
            output += renderer.render_node(cell, context)
            continue
        if index < len(align) and align[index] is not None:
            attrs = {'align': align[index]}
        else:
            attrs = {}
        output += f'<{tag}{renderer.render_attrs(attrs)}>{renderer.render_children(cell.children, context)}</{tag}>\n'
    output += '</tr>\n'
    return output


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
    if node.identifier not in footnotes.definitions:  # pragma: no cover
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
