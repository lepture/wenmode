from __future__ import annotations

from dataclasses import dataclass

from wenmode import HTMLRenderer, Parser
from wenmode.directives import Admonition, Figure, TableOfContents
from wenmode.nodes import (
    Blockquote,
    Code,
    ContainerDirective,
    DefinitionDescription,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    InlineMath,
    LeafDirective,
    Link,
    ListItem,
    Math,
    Node,
    Paragraph,
    Parent,
    Root,
    Table,
    TableCell,
    TableRow,
    Text,
)
from wenmode.renderers import RenderContext
from wenmode.rules import Footnote
from wenmode.toc import render_toc_html


@dataclass
class CustomElement(Parent):
    type: str = 'customElement'


def root_with_footnote_definitions(children: list[Node]) -> Root:
    root = Root(children=children)
    root.footnote_definitions = {
        child.identifier: child for child in children if isinstance(child, FootnoteDefinition)
    }
    return root


def test_html_renderer_custom_elements_require_registered_handler() -> None:
    node = Paragraph(children=[CustomElement(children=[Text(value='marked')])])

    assert HTMLRenderer().render(node) == '<p>marked</p>\n'

    @HTMLRenderer.register('customElement')
    def render_custom_element(renderer: HTMLRenderer, node: CustomElement, context: RenderContext) -> str:
        attrs = renderer.render_attrs({'data-custom': 'yes', 'hidden': False})
        return f'<mark{attrs}>{renderer.render_children(node.children, context)}</mark>'

    assert HTMLRenderer().render(node) == '<p><mark data-custom="yes">marked</mark></p>\n'


def test_html_renderer_always_escapes_text_code_and_attrs() -> None:
    node = Root(
        children=[
            Paragraph(
                children=[
                    Text(value='<span>x</span> & y'),
                    InlineCode(value='<code>'),
                    Link(url='/a?x=1&y=2', title='<title>', children=[Text(value='<link>')]),
                ]
            ),
            Code(value='<raw>\n', lang='html<script>'),
        ]
    )

    assert HTMLRenderer().render(node) == (
        '<p>&lt;span&gt;x&lt;/span&gt; &amp; y'
        '<code>&lt;code&gt;</code>'
        '<a href="/a?x=1&amp;y=2" title="&lt;title&gt;">&lt;link&gt;</a></p>\n'
        '<pre><code class="language-html&lt;script&gt;">&lt;raw&gt;\n</code></pre>\n'
    )
    assert HTMLRenderer(escape=False).render(node) == HTMLRenderer().render(node)


def test_html_renderer_escapes_raw_html_by_default() -> None:
    node = Root(
        children=[
            Heading(depth=1, children=[Text(value='h1')]),
            Html(value='<div>div</div>\n'),
            Paragraph(children=[Text(value='a '), Html(value='<span>b</span>')]),
        ]
    )

    assert HTMLRenderer().render(node) == (
        '<h1>h1</h1>\n&lt;div&gt;div&lt;/div&gt;\n<p>a &lt;span&gt;b&lt;/span&gt;</p>\n'
    )
    assert HTMLRenderer(escape=False).render(node) == '<h1>h1</h1>\n<div>div</div>\n<p>a <span>b</span></p>\n'


def test_html_renderer_sanitizes_link_and_image_urls_by_default() -> None:
    node = Root(
        children=[
            Paragraph(
                children=[
                    Link(url='javascript:alert(1)', children=[Text(value='bad link')]),
                    Text(value=' '),
                    Image(url='java\nscript:alert(1)', alt='bad image'),
                    Text(value=' '),
                    Link(url='/safe?x=1&y=2', children=[Text(value='relative')]),
                    Text(value=' '),
                    Link(url='mailto:me@example.com', children=[Text(value='mail')]),
                ]
            ),
        ]
    )

    assert HTMLRenderer().render(node) == (
        '<p><a>bad link</a> '
        '<img alt="bad image" /> '
        '<a href="/safe?x=1&amp;y=2">relative</a> '
        '<a href="mailto:me@example.com">mail</a></p>\n'
    )


def test_html_renderer_can_disable_url_sanitization() -> None:
    node = Paragraph(children=[Link(url='javascript:alert(1)', children=[Text(value='bad')])])

    assert HTMLRenderer(sanitize_urls=False).render(node) == '<p><a href="javascript:alert(1)">bad</a></p>\n'


def test_html_renderer_outputs_single_footnote() -> None:
    node = root_with_footnote_definitions(
        [
            Paragraph(children=[Text(value='a'), FootnoteReference(identifier='one', label='one')]),
            FootnoteDefinition(identifier='one', label='one', children=[Paragraph(children=[Text(value='note')])]),
        ]
    )

    assert HTMLRenderer().render(node) == (
        '<p>a<sup><a href="#user-content-fn-one" id="user-content-fnref-one" '
        'data-footnote-ref aria-describedby="footnote-label">1</a></sup></p>\n'
        '<section data-footnotes class="footnotes">\n'
        '<h2 class="sr-only" id="footnote-label">Footnotes</h2>\n'
        '<ol>\n'
        '<li id="user-content-fn-one">\n'
        '<p>note <a href="#user-content-fnref-one" data-footnote-backref '
        'class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>\n'
        '</li>\n'
        '</ol>\n'
        '</section>\n'
    )


def test_html_renderer_orders_multiple_footnotes_by_first_reference() -> None:
    node = root_with_footnote_definitions(
        [
            FootnoteDefinition(identifier='one', label='one', children=[Paragraph(children=[Text(value='one')])]),
            FootnoteDefinition(identifier='two', label='two', children=[Paragraph(children=[Text(value='two')])]),
            Paragraph(
                children=[
                    FootnoteReference(identifier='two', label='two'),
                    Text(value=' '),
                    FootnoteReference(identifier='one', label='one'),
                ]
            ),
        ]
    )

    html = HTMLRenderer().render(node)

    assert html.index('<li id="user-content-fn-two">') < html.index('<li id="user-content-fn-one">')
    assert 'id="user-content-fnref-two" data-footnote-ref aria-describedby="footnote-label">1</a>' in html
    assert 'id="user-content-fnref-one" data-footnote-ref aria-describedby="footnote-label">2</a>' in html


def test_html_renderer_reuses_number_for_repeated_footnote_references() -> None:
    node = root_with_footnote_definitions(
        [
            Paragraph(
                children=[
                    FootnoteReference(identifier='one', label='one'),
                    Text(value=' '),
                    FootnoteReference(identifier='one', label='one'),
                ]
            ),
            FootnoteDefinition(identifier='one', label='one', children=[Paragraph(children=[Text(value='note')])]),
        ]
    )

    html = HTMLRenderer().render(node)

    assert html.count('aria-describedby="footnote-label">1</a></sup>') == 2
    assert 'id="user-content-fnref-one-2"' in html
    assert 'href="#user-content-fnref-one-2" data-footnote-backref' in html


def test_html_renderer_reuses_instance_without_leaking_footnote_state() -> None:
    parser = Parser([Footnote])
    renderer = HTMLRenderer()
    root = parser.parse('a[^one]\n\n[^one]: note\n')

    first = renderer.render(root)
    second = renderer.render(root)

    assert second == first
    assert 'id="user-content-fnref-one-2"' not in second


def test_html_renderer_escapes_footnotes() -> None:
    node = root_with_footnote_definitions(
        [
            Paragraph(children=[FootnoteReference(identifier='a<b', label='a<b')]),
            FootnoteDefinition(identifier='a<b', label='a<b', children=[Paragraph(children=[Text(value='<note>')])]),
        ]
    )

    html = HTMLRenderer().render(node)

    assert 'href="#user-content-fn-a%3Cb"' in html
    assert '<p>&lt;note&gt; <a href="#user-content-fnref-a%3Cb"' in html


def test_html_renderer_outputs_math_nodes() -> None:
    node = Root(
        children=[
            Paragraph(children=[Text(value='a '), InlineMath(value='x < y')]),
            Math(value='x & y\n'),
        ]
    )

    assert HTMLRenderer().render(node) == (
        '<p>a <span class="math math-inline">x &lt; y</span></p>\n'
        '<div class="math math-display">x &amp; y\n</div>\n'
    )


def test_html_renderer_edge_branches() -> None:
    renderer = HTMLRenderer()
    context = renderer.create_context()

    assert renderer.render_attrs({'disabled': True, 'hidden': False, 'skip': None}) == ' disabled'
    assert renderer.render_list_item(Text(value='raw'), loose=False, context=context) == 'raw'
    assert renderer.render(ListItem(), context) == '<li></li>\n'
    assert renderer.render(ListItem(checked=False, children=[Paragraph(children=[Text(value='task')])])) == (
        '<li><input disabled="" type="checkbox"> task</li>\n'
    )
    assert renderer.render(
        ListItem(checked=False, spread=True, children=[Paragraph(children=[Text(value='task')])])
    ) == ('<li>\n<p><input disabled="" type="checkbox"> task</p>\n</li>\n')
    assert renderer.render(ListItem(checked=False, spread=True, children=[Blockquote(children=[])])) == (
        '<li>\n<input disabled="" type="checkbox"> <blockquote>\n</blockquote>\n</li>\n'
    )
    assert renderer.render(DefinitionDescription(spread=True, children=[Paragraph(children=[Text(value='x')])])) == (
        '<dd>\n<p>x</p>\n</dd>\n'
    )

    empty_context = renderer.create_context()
    assert renderer.render_footnote_section(empty_context) == ''
    missing_context = renderer.create_context()
    missing_context.footnotes.order.append('missing')
    assert renderer.render_footnote_section(missing_context) == (
        '<section data-footnotes class="footnotes">\n'
        '<h2 class="sr-only" id="footnote-label">Footnotes</h2>\n'
        '<ol>\n'
        '</ol>\n</section>\n'
    )
    assert renderer.render_footnote_definition_content(FootnoteDefinition(children=[Text(value='loose')]), context) == (
        'loose'
    )
    assert renderer.render(FootnoteReference(identifier='missing', label='<missing>')) == '[^&lt;missing&gt;]'

    assert renderer.render(Table()) == '<table>\n</table>\n'
    assert (
        renderer.render(Table(children=[Text(value='caption')], align=[]))
        == '<table>\n<thead>\ncaption</thead>\n</table>\n'
    )
    assert renderer.render(TableRow(children=[Text(value='raw'), TableCell(children=[Text(value='cell')])])) == (
        '<tr>\nraw<td>cell</td>\n</tr>\n'
    )
    assert renderer.render(TableCell(children=[Text(value='cell')])) == '<td>cell</td>'


def test_html_directive_renderers_without_labels_and_toc_fallbacks() -> None:
    renderer = HTMLRenderer(directives=[Admonition(), Figure(), TableOfContents()])
    root = Root(
        children=[
            ContainerDirective(name='note', children=[Paragraph(children=[Text(value='body')])]),
            ContainerDirective(name='figure', children=[Paragraph(children=[Text(value='image')])]),
            LeafDirective(name='toc', attributes={'min': 'bad'}, children=[Text(value='Contents')]),
        ]
    )

    assert renderer.render(root) == (
        '<aside class="admonition admonition-note">\n<p>body</p>\n</aside>\n<figure>\n<p>image</p>\n</figure>\n'
    )
    assert TableOfContents().render(HTMLRenderer(), LeafDirective(name='toc'), renderer.create_context()) == ''
    assert render_toc_html([], label='Empty') == ''
