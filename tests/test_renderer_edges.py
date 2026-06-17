from __future__ import annotations

from wenmode import HTMLRenderer, MarkdownRenderer
from wenmode.directives import Admonition, Figure, TableOfContents
from wenmode.nodes import (
    Blockquote,
    BlockSpoiler,
    Code,
    ContainerDirective,
    DefinitionDescription,
    FootnoteDefinition,
    FootnoteReference,
    Html,
    Image,
    InlineCode,
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
)
from wenmode.renderers.base import RenderContext
from wenmode.renderers.html import FootnoteRenderState, HTMLRenderContext
from wenmode.renderers.markdown import delimiter_for_align, normalize_table_row, quote_directive_attribute
from wenmode.toc import render_toc_html


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
    missing_context = HTMLRenderContext(footnotes=FootnoteRenderState(order=['missing']))
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
    assert TableOfContents().render(HTMLRenderer(), LeafDirective(name='toc'), HTMLRenderContext()) == ''
    assert render_toc_html([], label='Empty') == ''


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
