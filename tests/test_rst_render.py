from __future__ import annotations

from wenmode import RSTRenderer
from wenmode.nodes import (
    Abbreviation,
    Blockquote,
    BlockSpoiler,
    Break,
    Code,
    ContainerDirective,
    DefinitionDescription,
    DefinitionList,
    DefinitionTerm,
    Delete,
    Emphasis,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    InlineMath,
    InlineSpoiler,
    Insert,
    LeafDirective,
    Link,
    List,
    ListItem,
    Mark,
    Math,
    Paragraph,
    Root,
    Ruby,
    Strong,
    Subscript,
    Superscript,
    Table,
    TableCell,
    TableRow,
    Text,
    TextDirective,
    ThematicBreak,
)


def test_rst_renderer_outputs_inline_nodes() -> None:
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
                    InlineMath(value='x + y'),
                    Text(value=' '),
                    Link(url='/url', title='T', children=[Text(value='link')]),
                    Text(value=' '),
                    Image(url='/img.png', alt='alt'),
                ]
            ),
        ]
    )

    assert RSTRenderer().render(node) == (
        'Title\n'
        '-----\n\n'
        'Hello *em* **strong** ``code`` :math:`x + y` `link </url>`__ |image-1|\n\n'
        '.. |image-1| image:: /img.png\n'
        '   :alt: alt\n'
    )


def test_rst_renderer_outputs_block_nodes() -> None:
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
            Code(value='print(1)\n', lang='py'),
            ThematicBreak(),
            Paragraph(children=[Text(value='a'), Break(), Text(value='b')]),
        ]
    )

    assert RSTRenderer().render(node) == (
        '   quote\n\n'
        '- one\n'
        '- two\n\n'
        '3. three\n'
        '4. four\n\n'
        '.. code-block:: py\n\n'
        '   print(1)\n\n'
        '----\n\n'
        'a\n'
        'b\n'
    )


def test_rst_renderer_outputs_tables_definitions_and_directives() -> None:
    node = Root(
        children=[
            DefinitionList(
                children=[
                    DefinitionTerm(children=[Text(value='Apple')]),
                    DefinitionDescription(children=[Paragraph(children=[Text(value='Fruit')])]),
                ]
            ),
            Table(
                children=[
                    TableRow(
                        children=[
                            TableCell(children=[Text(value='Name')]),
                            TableCell(children=[Text(value='Value')]),
                        ]
                    ),
                    TableRow(
                        children=[
                            TableCell(children=[Text(value='A')]),
                            TableCell(children=[Text(value='1')]),
                        ]
                    ),
                ],
            ),
            ContainerDirective(
                name='note',
                attributes={'class': 'warning'},
                children=[
                    Paragraph(children=[Text(value='Important')], data={'directiveLabel': True}),
                    Paragraph(children=[Text(value='Body.')]),
                ],
            ),
        ]
    )

    assert RSTRenderer().render(node) == (
        'Apple\n'
        '  Fruit\n\n'
        '====  =====\n'
        'Name  Value\n'
        '====  =====\n'
        'A     1\n'
        '====  =====\n\n'
        '.. note:: Important\n'
        '   :class: warning\n\n'
        '   Body.\n'
    )


def test_rst_renderer_outputs_footnotes() -> None:
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

    assert RSTRenderer().render(node) == 'a[#one]_\n\n.. [#one] note\n\n.. [#two] first\n\n   second\n'


def test_rst_renderer_outputs_math_nodes() -> None:
    node = Root(
        children=[
            Paragraph(children=[Text(value='a '), InlineMath(value='x + y')]),
            Math(value='z = 1\n'),
        ]
    )

    assert RSTRenderer().render(node) == 'a :math:`x + y`\n\n.. math::\n\n   z = 1\n'


def test_rst_renderer_outputs_extended_inline_nodes() -> None:
    node = Paragraph(
        children=[
            Abbreviation(title='HyperText', children=[Text(value='HTML')]),
            Text(value=' '),
            Abbreviation(children=[Text(value='W3C')]),
            Text(value=' '),
            Delete(children=[Text(value='gone')]),
            Text(value=' '),
            Mark(children=[Text(value='mark')]),
            Text(value=' '),
            Insert(children=[Text(value='insert')]),
            Text(value=' '),
            Superscript(children=[Text(value='2')]),
            Text(value=' '),
            Subscript(children=[Text(value='n')]),
            Text(value=' '),
            Ruby(segments=[{'base': '漢', 'text': 'kan'}]),
            Text(value=' '),
            InlineSpoiler(children=[Text(value='secret')]),
            Text(value=' '),
            TextDirective(name='kbd', children=[Text(value='Ctrl+C')]),
        ]
    )

    assert RSTRenderer().render(node) == (
        ':abbr:`HTML (HyperText)` W3C gone mark insert :sup:`2` :sub:`n` 漢 (kan) secret :kbd:`Ctrl+C`\n\n'
    )


def test_rst_renderer_edge_branches_for_empty_and_direct_nodes() -> None:
    renderer = RSTRenderer()

    assert renderer.render(Root()) == ''
    context = renderer.create_context(Root())
    assert renderer.render(Image(url='/collected.png'), context) == '|image-1|'
    assert renderer.render(Root(), context) == '.. |image-1| image:: /collected.png\n'
    assert renderer.render(Root(children=[Image(url='/only.png', title='Only')])) == (
        '|image-1|\n\n.. |image-1| image:: /only.png\n   :title: Only\n'
    )
    assert renderer.render(List(children=[ListItem(checked=True)])) == '- [x]\n\n'
    assert renderer.render(List(children=[ListItem(checked=False)])) == '- [ ]\n\n'
    assert renderer.render(List(children=[Text(value='raw')])) == 'raw\n\n'
    assert renderer.render(ListItem(children=[Text(value='direct')])) == 'direct'
    assert renderer.render(DefinitionDescription()) == '  \n'
    assert renderer.render(
        DefinitionDescription(
            children=[
                Paragraph(children=[Text(value='first')]),
                Paragraph(children=[Text(value='second')]),
            ]
        )
    ) == '  first\n\n  second\n'
    assert renderer.render(Blockquote()) == ''
    assert renderer.render(BlockSpoiler()) == '.. admonition:: Spoiler\n\n'
    assert renderer.render(BlockSpoiler(children=[Paragraph(children=[Text(value='hidden')])])) == (
        '.. admonition:: Spoiler\n\n   hidden\n\n'
    )
    assert renderer.render(Code(value='plain')) == '::\n\n   plain\n\n'
    assert renderer.render(Html(value='<span>x</span>')) == '<span>x</span>'
    assert renderer.render(Html(value='<div>\nx</div>\n')) == '.. raw:: html\n\n   <div>\n   x</div>\n\n'
    assert renderer.render(Image(url='/direct.png', alt='Direct', title='Title')) == (
        '.. image:: /direct.png\n   :alt: Direct\n   :title: Title\n\n'
    )
    assert renderer.render(Image(url='/plain.png')) == '.. image:: /plain.png\n\n'
    assert renderer.render(FootnoteDefinition(identifier='bad label!', label='bad label!')) == '.. [#bad-label]\n\n'


def test_rst_renderer_directive_edge_branches() -> None:
    renderer = RSTRenderer()

    assert renderer.render(LeafDirective(name='toc')) == '.. toc::\n\n'
    assert renderer.render(LeafDirective(name='note', attributes={'id': 'intro', 'empty': ''})) == (
        '.. note::\n   :name: intro\n   :empty:\n\n'
    )
    assert renderer.render(LeafDirective(name='note', children=[Text(value='Title')])) == '.. note:: Title\n\n'
    assert renderer.render(ContainerDirective(name='note')) == '.. note::\n\n'
    assert renderer.render(ContainerDirective(name='note', attributes={'class': 'warning'})) == (
        '.. note::\n   :class: warning\n\n'
    )
    assert renderer.render(
        ContainerDirective(
            name='note',
            children=[
                Text(value='lead'),
                Paragraph(children=[Text(value='body')]),
            ],
        )
    ) == '.. note::\n\n   leadbody\n\n'


def test_rst_renderer_table_edge_branches() -> None:
    renderer = RSTRenderer()

    assert renderer.render(Table()) == ''
    assert renderer.render(Table(children=[TableRow()])) == ''
    assert renderer.render(TableRow()) == ''
    assert renderer.render(TableRow(children=[TableCell(children=[Text(value='cell')])])) == 'cell\n'
    assert renderer.render(TableCell(children=[Text(value='cell')])) == 'cell'
