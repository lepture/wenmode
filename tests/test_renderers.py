from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from wenmode import HTMLRenderer, MarkdownRenderer, Wenmode, commonmark
from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    Emphasis,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    HtmlAttrValue,
    Image,
    InlineCode,
    InlineMath,
    Link,
    List,
    ListItem,
    Literal,
    Math,
    Node,
    Paragraph,
    Parent,
    Root,
    Strong,
    Text,
    ThematicBreak,
)
from wenmode.renderers import BaseRenderer
from wenmode.rules import Footnote, MathBlock
from wenmode.rules import InlineMath as InlineMathRule


@dataclass
class CustomLiteral(Literal):
    type: str = 'customLiteral'


@dataclass
class CustomParent(Parent):
    type: str = 'customParent'


@dataclass
class CustomElement(Parent):
    html_tag: ClassVar[str | None] = 'mark'
    type: str = 'customElement'

    def get_html_attrs(self) -> dict[str, HtmlAttrValue]:
        return {'data-custom': 'yes', 'hidden': False, 'href': 'javascript:alert(1)'}


@dataclass
class CustomVoidElement(Node):
    html_tag: ClassVar[str | None] = 'custom-void'
    html_void: ClassVar[bool] = True
    type: str = 'customVoidElement'

    def get_html_attrs(self) -> dict[str, HtmlAttrValue]:
        return {'checked': True, 'label': '<x>'}


def test_renderer_registers_custom_node_handler() -> None:
    @HTMLRenderer.register('customLiteral')
    def render_custom_literal(renderer: HTMLRenderer, node: CustomLiteral) -> str:
        return f'<custom>{renderer.escape(node.value)}</custom>'

    assert HTMLRenderer().render(CustomLiteral(value='<x>')) == '<custom>&lt;x&gt;</custom>'


def test_html_renderer_uses_node_html_tag_and_attrs_without_registration() -> None:
    node = Root(
        children=[
            Paragraph(children=[CustomElement(children=[Text(value='marked')]), CustomVoidElement()]),
        ]
    )

    assert HTMLRenderer().render(node) == (
        '<p><mark data-custom="yes" href="javascript:alert(1)">marked</mark>'
        '<custom-void checked label="&lt;x&gt;" /></p>\n'
    )


def test_nodes_omit_empty_html_attrs() -> None:
    assert Link(url='/url').get_html_attrs() == {'href': '/url'}
    assert Link(url='/url', title='title').get_html_attrs() == {'href': '/url', 'title': 'title'}
    assert Image(url='/img.png', alt='alt').get_html_attrs() == {'src': '/img.png', 'alt': 'alt'}


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


def test_base_renderer_unknown_nodes_fall_back_to_children_or_value() -> None:
    renderer = BaseRenderer()

    assert renderer.render(CustomParent(children=[CustomLiteral(value='a'), CustomLiteral(value='b')])) == 'ab'
    assert renderer.render(CustomLiteral(value='literal')) == 'literal'


def test_markdown_renderer_outputs_inline_nodes() -> None:
    node = Root(
        children=[
            Heading(depth=2, children=[Text(value='Title')]),
            Paragraph(
                children=[
                    Text(value='Hello '),
                    Emphasis(children=[Text(value='em')]),
                    Text(value=' '),
                    Strong(children=[Text(value='strong')]),
                    Text(value=' '),
                    InlineCode(value='code'),
                    Text(value=' '),
                    Link(url='/url', title='T', children=[Text(value='link')]),
                    Text(value=' '),
                    Image(url='/img.png', alt='alt'),
                ]
            ),
        ]
    )

    assert (
        MarkdownRenderer().render(node)
        == '## Title\n\nHello *em* **strong** `code` [link](/url "T") ![alt](/img.png)\n'
    )


def test_markdown_renderer_outputs_block_nodes() -> None:
    node = Root(
        children=[
            Blockquote(children=[Paragraph(children=[Text(value='quote')])]),
            List(
                children=[
                    ListItem(children=[Paragraph(children=[Text(value='one')])]),
                    ListItem(children=[Paragraph(children=[Text(value='two')])]),
                ]
            ),
            List(
                ordered=True,
                start=3,
                children=[
                    ListItem(children=[Paragraph(children=[Text(value='three')])]),
                    ListItem(children=[Paragraph(children=[Text(value='four')])]),
                ],
            ),
            List(
                spread=True,
                children=[
                    ListItem(
                        spread=True,
                        children=[
                            Paragraph(children=[Text(value='loose')]),
                            Paragraph(children=[Text(value='item')]),
                        ],
                    ),
                    ListItem(children=[Paragraph(children=[Text(value='next')])]),
                ],
            ),
            Code(value='print(1)\n', lang='py'),
            ThematicBreak(),
            Paragraph(children=[Text(value='a'), Break(), Text(value='b')]),
        ]
    )

    assert MarkdownRenderer().render(node) == (
        '> quote\n\n'
        '- one\n'
        '- two\n\n'
        '3. three\n'
        '4. four\n\n'
        '- loose\n'
        '  \n'
        '  item\n\n'
        '- next\n\n'
        '```py\n'
        'print(1)\n'
        '```\n\n'
        '---\n\n'
        'a  \n'
        'b\n'
    )


def test_markdown_renderer_round_trips_to_equivalent_html() -> None:
    parser = Wenmode(commonmark)
    html_renderer = HTMLRenderer()
    markdown_renderer = MarkdownRenderer()
    markdown = (
        '# A\n\n'
        '> hi *there*\n\n'
        '- one\n'
        '- two\n\n'
        '```py\n'
        'print(1)\n'
        '```\n\n'
        '[link](/url "t") and ![alt](/img.png)\n'
    )

    html = html_renderer.render(parser.parse(markdown))
    rendered_markdown = markdown_renderer.render(parser.parse(markdown))

    assert html_renderer.render(parser.parse(rendered_markdown)) == html


def test_html_renderer_outputs_single_footnote() -> None:
    node = Root(
        children=[
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
    node = Root(
        children=[
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
    node = Root(
        children=[
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


def test_html_renderer_escapes_footnotes() -> None:
    node = Root(
        children=[
            Paragraph(children=[FootnoteReference(identifier='a<b', label='a<b')]),
            FootnoteDefinition(identifier='a<b', label='a<b', children=[Paragraph(children=[Text(value='<note>')])]),
        ]
    )

    html = HTMLRenderer().render(node)

    assert 'href="#user-content-fn-a%3Cb"' in html
    assert '<p>&lt;note&gt; <a href="#user-content-fnref-a%3Cb"' in html


def test_markdown_renderer_outputs_footnotes() -> None:
    node = Root(
        children=[
            Paragraph(children=[Text(value='a'), FootnoteReference(identifier='one', label='one')]),
            FootnoteDefinition(identifier='one', label='one', children=[Paragraph(children=[Text(value='note')])]),
            FootnoteDefinition(
                identifier='two',
                label='two',
                children=[
                    Paragraph(children=[Text(value='first')]),
                    Paragraph(children=[Text(value='second')]),
                ],
            ),
        ]
    )

    assert MarkdownRenderer().render(node) == 'a[^one]\n\n[^one]: note\n\n[^two]: first\n  \n  second\n'


def test_markdown_renderer_round_trips_footnotes_to_equivalent_html() -> None:
    parser = Wenmode([Footnote])
    html_renderer = HTMLRenderer()
    markdown_renderer = MarkdownRenderer()
    markdown = 'a[^one]\n\n[^one]: first\n  \n  second\n'

    html = html_renderer.render(parser.parse(markdown))
    rendered_markdown = markdown_renderer.render(parser.parse(markdown))

    assert html_renderer.render(parser.parse(rendered_markdown)) == html


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


def test_markdown_renderer_outputs_math_nodes() -> None:
    node = Root(
        children=[
            Paragraph(children=[Text(value='a '), InlineMath(value='x + y')]),
            Math(value='z = 1\n'),
        ]
    )

    assert MarkdownRenderer().render(node) == 'a $x + y$\n\n$$\nz = 1\n$$\n'


def test_markdown_renderer_round_trips_math_to_equivalent_html() -> None:
    parser = Wenmode([MathBlock, InlineMathRule])
    html_renderer = HTMLRenderer()
    markdown_renderer = MarkdownRenderer()
    markdown = 'inline $x < y$\n\n$$\na & b\n$$\n'

    html = html_renderer.render(parser.parse(markdown))
    rendered_markdown = markdown_renderer.render(parser.parse(markdown))

    assert html_renderer.render(parser.parse(rendered_markdown)) == html
