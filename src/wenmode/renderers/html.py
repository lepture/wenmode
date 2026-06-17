from __future__ import annotations

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from typing import Protocol
from urllib.parse import quote, urlsplit

from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    ContainerDirective,
    Delete,
    DirectiveNode,
    FootnoteDefinition,
    FootnoteReference,
    Html,
    HtmlAttrValue,
    Image,
    InlineMath,
    LeafDirective,
    Link,
    List,
    ListItem,
    Math,
    Node,
    Paragraph,
    Root,
    Table,
    TableCell,
    TableRow,
    Text,
    TextDirective,
)

from .base import BaseRenderer, RenderContext

SOFT_BREAK_SPACE_RE = re.compile(r'(?<! ) (?=\r?\n)')


@dataclass
class FootnoteRenderState:
    definitions: dict[str, FootnoteDefinition] = field(default_factory=dict)
    numbers: dict[str, int] = field(default_factory=dict)
    order: list[str] = field(default_factory=list)
    reference_ids: dict[str, list[str]] = field(default_factory=dict)


@dataclass
class HTMLRenderContext(RenderContext):
    footnotes: FootnoteRenderState = field(default_factory=FootnoteRenderState)


class DirectiveHtmlRenderer(Protocol):
    def render(self, renderer: HTMLRenderer, node: DirectiveNode, context: HTMLRenderContext) -> str | None:
        pass


class HTMLRenderer(BaseRenderer):
    allowed_url_schemes = frozenset({'http', 'https', 'irc', 'ircs', 'mailto', 'tel'})

    def __init__(
        self,
        escape: bool = True,
        sanitize_urls: bool = True,
        directives: Iterable[DirectiveHtmlRenderer] = (),
    ) -> None:
        self.escape_enabled = escape
        self.sanitize_urls = sanitize_urls
        self.directives = list(directives)

    def create_context(self, node: Node | None = None) -> HTMLRenderContext:
        definitions = node.footnote_definitions if isinstance(node, Root) else None
        return HTMLRenderContext(FootnoteRenderState(definitions=definitions or {}))

    def register_directive_renderer(self, directive: DirectiveHtmlRenderer) -> None:
        self.directives.append(directive)

    def render_list_item(self, item: Node, loose: bool, context: HTMLRenderContext) -> str:
        if not isinstance(item, ListItem):
            return self.render_node(item, context)
        if not item.children:
            return '<li></li>\n'
        if not loose:
            prefix = '<li>' if isinstance(item.children[0], Paragraph) else '<li>\n'
            parts: list[str] = []
            for index, child in enumerate(item.children):
                if isinstance(child, Paragraph):
                    marker = self.render_task_marker(item) if index == 0 else ''
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
        if not self.escape_enabled:
            return value
        return self.escape_html(value)

    def escape_html(self, value: str) -> str:
        return value.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

    def render_unknown(self, node: Node, context: RenderContext) -> str:
        tag = node.get_html_tag()
        if tag is not None:
            return self.render_element(node, tag, context)
        return super().render_unknown(node, context)

    def render_element(self, node: Node, tag: str, context: RenderContext) -> str:
        attrs = self.render_attrs(node.get_html_attrs())
        if node.html_void:
            return f'<{tag}{attrs} />' + ('\n' if node.block else '')

        content = self.render_element_content(node, context)
        return f'<{tag}{attrs}>{content}</{tag}>' + ('\n' if node.block else '')

    def render_element_content(self, node: Node, context: RenderContext) -> str:
        children = getattr(node, 'children', None)
        if isinstance(children, list):
            return self.render_children(children, context)

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
        for directive in self.directives:
            rendered = directive.render(self, node, context)
            if rendered is not None:
                return rendered
        return None


@HTMLRenderer.register('root')
def render_root(renderer: HTMLRenderer, node: Root, context: HTMLRenderContext) -> str:
    out = renderer.render_children(node.children, context)
    if node.footnote_definitions:
        out += renderer.render_footnote_section(context)
    return out


@HTMLRenderer.register('blockquote')
def render_blockquote(renderer: HTMLRenderer, node: Blockquote, context: HTMLRenderContext) -> str:
    return '<blockquote>\n' + renderer.render_children(node.children, context) + '</blockquote>\n'


@HTMLRenderer.register('list')
def render_list(renderer: HTMLRenderer, node: List, context: HTMLRenderContext) -> str:
    tag = 'ol' if node.ordered else 'ul'
    start = f' start="{node.start}"' if node.ordered and node.start not in (None, 1) else ''
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


@HTMLRenderer.register('textDirective')
def render_text_directive(renderer: HTMLRenderer, node: TextDirective, context: HTMLRenderContext) -> str:
    rendered = renderer.render_directive(node, context)
    if rendered is not None:
        return rendered
    return renderer.render_children(node.children, context)


@HTMLRenderer.register('leafDirective')
def render_leaf_directive(renderer: HTMLRenderer, node: LeafDirective, context: HTMLRenderContext) -> str:
    rendered = renderer.render_directive(node, context)
    if rendered is not None:
        return rendered
    return renderer.render_children(node.children, context)


@HTMLRenderer.register('containerDirective')
def render_container_directive(renderer: HTMLRenderer, node: ContainerDirective, context: HTMLRenderContext) -> str:
    rendered = renderer.render_directive(node, context)
    if rendered is not None:
        return rendered
    return renderer.render_children(node.children, context)


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
        attrs = {'align': align[index]} if index < len(align) and align[index] is not None else {}
        output.append(
            f'<{tag}{renderer.render_attrs(attrs)}>{renderer.render_children(cell.children, context)}</{tag}>\n'
        )
    output.append('</tr>\n')
    return ''.join(output)


@HTMLRenderer.register('code')
def render_code(renderer: HTMLRenderer, node: Code, context: HTMLRenderContext) -> str:
    lang = f' class="language-{renderer.escape_html(node.lang)}"' if node.lang else ''
    return f'<pre><code{lang}>{renderer.escape_html(node.value)}</code></pre>\n'


@HTMLRenderer.register('math')
def render_math(renderer: HTMLRenderer, node: Math, context: HTMLRenderContext) -> str:
    return f'<div class="math math-display">{renderer.escape_html(node.value)}</div>\n'


@HTMLRenderer.register('html')
def render_html(renderer: HTMLRenderer, node: Html, context: HTMLRenderContext) -> str:
    if node.data and node.data.get('escaped'):
        return node.value
    return renderer.escape(node.value)


@HTMLRenderer.register('text')
def render_text(renderer: HTMLRenderer, node: Text, context: HTMLRenderContext) -> str:
    return renderer.escape_html(SOFT_BREAK_SPACE_RE.sub('', node.value))


@HTMLRenderer.register('inlineMath')
def render_inline_math(renderer: HTMLRenderer, node: InlineMath, context: HTMLRenderContext) -> str:
    return f'<span class="math math-inline">{renderer.escape_html(node.value)}</span>'


@HTMLRenderer.register('link')
def render_link(renderer: HTMLRenderer, node: Link, context: HTMLRenderContext) -> str:
    attrs = node.get_html_attrs()
    href = renderer.sanitize_url(node.url)
    if href is None:
        attrs.pop('href', None)
    else:
        attrs['href'] = href
    return f'<a{renderer.render_attrs(attrs)}>{renderer.render_children(node.children, context)}</a>'


@HTMLRenderer.register('image')
def render_image(renderer: HTMLRenderer, node: Image, context: HTMLRenderContext) -> str:
    attrs = node.get_html_attrs()
    src = renderer.sanitize_url(node.url)
    if src is None:
        attrs.pop('src', None)
    else:
        attrs['src'] = src
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
    reference_id = base_reference_id if not references else f'{base_reference_id}-{len(references) + 1}'
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
