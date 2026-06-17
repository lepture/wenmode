from __future__ import annotations

from wenmode import HTMLRenderer, MarkdownRenderer, Parser
from wenmode.nodes import (
    Blockquote,
    BlockSpoiler,
    Break,
    Code,
    ContainerDirective,
    DefinitionDescription,
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
from wenmode.presets import commonmark
from wenmode.renderers import RenderContext, delimiter_for_align, normalize_table_row, quote_directive_attribute
from wenmode.rules import Footnote, MathBlock
from wenmode.rules import InlineMath as InlineMathRule


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
    parser = Parser(commonmark)
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
    parser = Parser([Footnote])
    html_renderer = HTMLRenderer()
    markdown_renderer = MarkdownRenderer()
    markdown = 'a[^one]\n\n[^one]: first\n  \n  second\n'

    html = html_renderer.render(parser.parse(markdown))
    rendered_markdown = markdown_renderer.render(parser.parse(markdown))

    assert html_renderer.render(parser.parse(rendered_markdown)) == html


def test_markdown_renderer_outputs_math_nodes() -> None:
    node = Root(
        children=[
            Paragraph(children=[Text(value='a '), InlineMath(value='x + y')]),
            Math(value='z = 1\n'),
        ]
    )

    assert MarkdownRenderer().render(node) == 'a $x + y$\n\n$$\nz = 1\n$$\n'


def test_markdown_renderer_round_trips_math_to_equivalent_html() -> None:
    parser = Parser([MathBlock, InlineMathRule])
    html_renderer = HTMLRenderer()
    markdown_renderer = MarkdownRenderer()
    markdown = 'inline $x < y$\n\n$$\na & b\n$$\n'

    html = html_renderer.render(parser.parse(markdown))
    rendered_markdown = markdown_renderer.render(parser.parse(markdown))

    assert html_renderer.render(parser.parse(rendered_markdown)) == html


def test_markdown_renderer_edge_branches() -> None:
    renderer = MarkdownRenderer()

    assert renderer.render(Root()) == ''
    assert renderer.render(List(children=[Text(value='raw')])) == 'raw\n\n'
    assert renderer.render(List(children=[ListItem(checked=True)])) == '- [x]\n\n'
    assert renderer.render(List(children=[ListItem(checked=False)])) == '- [ ]\n\n'
    assert renderer.render(DefinitionDescription()) == ': \n'
    assert renderer.render(Blockquote()) == '>\n\n'
    assert renderer.render(BlockSpoiler()) == '>!\n\n'
    assert renderer.render(ContainerDirective(name='note')) == ':::note\n:::\n\n'
    assert renderer.render(Table()) == ''
    assert (
        renderer.render(
            Table(
                align=['left', None],
                children=[
                    TableRow(children=[TableCell(children=[Text(value='h1')]), TableCell(children=[Text(value='h2')])]),
                    TableRow(children=[TableCell(children=[Text(value='a')])]),
                ],
            )
        )
        == '| h1 | h2 |\n| :--- | --- |\n| a |  |\n\n'
    )
    assert renderer.render(TableRow(children=[TableCell(children=[Text(value='a')]), Text(value='skip')])) == '| a |\n'
    assert renderer.render(TableCell(children=[Text(value='a\nb')])) == 'a b'
    assert renderer.render(Code(value='contains ``` fence', meta='meta')) == '````meta\ncontains ``` fence\n````\n\n'
    assert renderer.render(Math(value='x')) == '$$\nx\n$$\n\n'
    assert renderer.render(Html(value='<x>\n')) == '<x>\n\n'
    assert renderer.render(InlineCode(value='`x`')) == '`` `x` ``'
    assert renderer.render(FootnoteDefinition(identifier='empty')) == '[^empty]:\n\n'
    assert renderer.render(Link(url='/a b(1)', title='a "quote"', children=[Text(value='link')])) == (
        '[link](</a b(1)> "a \\"quote\\"")'
    )
    assert renderer.render(Image(url='/a)b', alt='a*b', title='title')) == '![a\\*b](</a)b> "title")'
    assert renderer.render_directive_label(Node(type='bare'), RenderContext()) == ''
    assert renderer.render_directive_attributes({'id': '', 'class': '  ', 'empty': ''}) == '{empty}'
    assert renderer.render_directive_attributes({'key': 'needs space'}) == '{key="needs space"}'
    assert quote_directive_attribute('') == '""'
    assert quote_directive_attribute('simple') == 'simple'
    assert delimiter_for_align('left') == ':---'
    assert delimiter_for_align('right') == '---:'
    assert delimiter_for_align('center') == ':---:'
    assert delimiter_for_align(None) == '---'
    assert normalize_table_row(Text(value='not-row'), 2) == [TableCell(), TableCell()]
    assert normalize_table_row(TableRow(children=[TableCell(), TableCell()]), 1) == [TableCell()]
    assert renderer.render(ListItem(children=[Text(value='direct')])) == 'direct'
    assert renderer.render(DefinitionDescription(spread=True, children=[Paragraph(children=[Text(value='a')])])) == (
        ': a\n'
    )
    assert renderer.render(Html(value='<x>')) == '<x>'
