from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from wenmode import COMMON_MARK, HTMLRenderer, MarkdownRenderer, Wenmode
from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    Emphasis,
    Heading,
    Html,
    HtmlAttrValue,
    Image,
    InlineCode,
    Link,
    List,
    ListItem,
    Literal,
    Node,
    Paragraph,
    Parent,
    Root,
    Strong,
    Text,
    ThematicBreak,
)
from wenmode.renderers import BaseRenderer


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
        return {'data-custom': 'yes', 'hidden': False}


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
        '<p><mark data-custom="yes">marked</mark><custom-void checked label="&lt;x&gt;" /></p>\n'
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
    parser = Wenmode(COMMON_MARK)
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
