from __future__ import annotations

import re
from dataclasses import dataclass

import pytest

from wenmode import HTMLRenderer, MarkdownRenderer, Parser, Wenmode
from wenmode.directives import Admonition, Figure, TableOfContents
from wenmode.headings import Slugger, add_heading_ids, plain_text
from wenmode.nodes import (
    Blockquote,
    BlockSpoiler,
    Break,
    Code,
    ContainerDirective,
    DefinitionDescription,
    DefinitionList,
    DefinitionTerm,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    InlineMath,
    LeafDirective,
    Link,
    List,
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
    TextDirective,
)
from wenmode.nodes import (
    Emphasis as EmphasisNode,
)
from wenmode.parser import contains_emphasis_marker, merge_text
from wenmode.presets import commonmark, github
from wenmode.renderers import BaseRenderer
from wenmode.renderers.base import RenderContext
from wenmode.renderers.html import DirectiveHtmlRenderer, FootnoteRenderState, HTMLRenderContext
from wenmode.renderers.markdown import delimiter_for_align, normalize_table_row, quote_directive_attribute
from wenmode.rules import (
    Abbreviation,
    AtxHeading,
    BlockRule,
    ContinueRule,
    Emphasis,
    ExtendedAutolink,
    FencedCode,
    Footnote,
    HtmlBlock,
    InlineMath,
    InlineRule,
    MathBlock,
    Role,
    Rule,
    Strikethrough,
)
from wenmode.rules import (
    BlockSpoiler as BlockSpoilerRule,
)
from wenmode.rules import (
    Image as ImageRule,
)
from wenmode.rules import (
    LeafDirective as LeafDirectiveRule,
)
from wenmode.rules import (
    Link as LinkRule,
)
from wenmode.rules import (
    List as ListRule,
)
from wenmode.rules import (
    Table as TableRule,
)
from wenmode.rules import (
    TextDirective as TextDirectiveRule,
)
from wenmode.rules import directives as directives_module
from wenmode.rules import footnotes as footnotes_module
from wenmode.rules.blocks import html as html_block_module
from wenmode.rules.blocks.abbr import (
    ABBREVIATIONS_KEY,
    AbbreviationDefinition,
    AbbreviationState,
    parse_abbreviation_definition,
    replace_abbreviations,
    transform_abbreviations,
)
from wenmode.rules.blocks.definition_list import (
    DefinitionList as DefinitionListRule,
)
from wenmode.rules.blocks.definition_list import (
    collect_description_continuation,
    parse_following_items,
    parse_following_terms,
)
from wenmode.rules.blocks.directive import (
    ContainerDirective as ContainerDirectiveRule,
)
from wenmode.rules.blocks.directive import (
    FencedDirective,
    directive_label_children,
    parse_option_line,
)
from wenmode.rules.blocks.directive import (
    LeafDirective as LeafDirectiveBlockRule,
)
from wenmode.rules.blocks.fenced_code import strip_fence_indent
from wenmode.rules.blocks.heading import SetextHeading, resolve_heading_id_transform
from wenmode.rules.blocks.indented_code import strip_indent as strip_indented_code
from wenmode.rules.blocks.list import (
    MARKER_RE,
    apply_task_list_marker,
    blank_belongs_to_item,
    has_open_fence,
    parse_shallow_list,
    should_keep_blank_in_item,
)
from wenmode.rules.blocks.math import MathBlock as MathBlockRule
from wenmode.rules.blocks.spoiler import BLOCK_SPOILER_RE
from wenmode.rules.blocks.table import (
    has_unescaped_pipe,
    normalize_row,
    parse_delimiter_row,
    split_table_row,
)
from wenmode.rules.blocks.util import parse_shallow_block
from wenmode.rules.directives import (
    find_balanced,
    parse_attributes,
    parse_directive_head,
    parse_shortcuts,
    tokenize_attributes,
)
from wenmode.rules.footnotes import (
    Footnote as FootnoteRule,
)
from wenmode.rules.footnotes import (
    FootnoteDefinition as FootnoteDefinitionRule,
)
from wenmode.rules.footnotes import (
    collect_definition_lines,
    collect_footnote_definitions,
    has_later_continuation,
)
from wenmode.rules.footnotes import (
    strip_indent as strip_footnote_indent,
)
from wenmode.rules.inlines import emphasis as emphasis_module
from wenmode.rules.inlines import math as math_module
from wenmode.rules.inlines import strikethrough as strikethrough_module
from wenmode.rules.inlines.directive import TextDirective as TextDirectiveInlineRule
from wenmode.rules.inlines.directive import parse_role
from wenmode.rules.inlines.emphasis import (
    Delimiter,
    can_close,
    can_open,
    find_closing_delimiter,
    is_inside_code_span,
    parse_emphasis_sequence,
    process_delimiters,
)
from wenmode.rules.inlines.extended_autolink import ExtendedAutolink as ExtendedAutolinkRule
from wenmode.rules.inlines.link import (
    build_closing_bracket_map,
    closing_bracket_cache,
    closing_bracket_map,
    find_closing_bracket,
    find_closing_bracket_uncached,
    find_code_span_end,
    invalid_reference_label,
    normalize_optional_text,
    parse_destination,
    parse_direct_destination,
    parse_link_or_image,
    parse_title,
)
from wenmode.rules.inlines.link import (
    plain_text as link_plain_text,
)
from wenmode.rules.inlines.math import InlineMath as InlineMathRule
from wenmode.rules.inlines.math import find_closing_dollar
from wenmode.rules.inlines.ruby import Ruby as RubyRule
from wenmode.rules.inlines.ruby import parse_ruby_link, parse_ruby_segments
from wenmode.rules.inlines.strikethrough import find_closing_marker
from wenmode.rules.references import (
    ReferenceDefinition,
    parse_multiline_label_reference,
    parse_multiline_reference_title,
    parse_reference,
    parse_reference_destination,
    parse_reference_title,
)
from wenmode.rules.transforms import RootTransform
from wenmode.state import BlockState, StateStore, StreamBlockState, StreamLineBuffer
from wenmode.toc import collect_toc, render_toc_html


@dataclass
class WrapperNode(Node):
    child: Node | None = None
    children: list[Node] | None = None
    value: str | None = None
    type: str = 'wrapper'


@dataclass
class IdentifierNode(Node):
    identifier: str = ''
    type: str = 'identifier'


class SearchInline(InlineRule):
    order = 10

    def __init__(self) -> None:
        super().__init__('search_inline', r'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='search'), match.end()


class LaterSearchInline(InlineRule):
    order = 20

    def __init__(self) -> None:
        super().__init__('later_search_inline', r'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='later'), match.end()


class TriggerInline(InlineRule):
    order = 30

    def __init__(self) -> None:
        super().__init__('trigger_inline', r'x', 'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='trigger'), match.end()


def render_html(parser: Parser, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


def test_base_node_state_and_protocol_edges() -> None:
    wrapper = WrapperNode(child=Text(value='child'), children=[Text(value='nested')], value='literal')
    assert wrapper.to_ast() == {
        'type': 'wrapper',
        'child': {'type': 'text', 'value': 'child'},
        'children': [{'type': 'text', 'value': 'nested'}],
        'value': 'literal',
    }

    renderer = BaseRenderer()
    context = RenderContext()
    assert renderer.render(WrapperNode(value='x'), context) == 'x'
    assert list(renderer.render_iter([WrapperNode(value='a'), WrapperNode(value='b')])) == ['a', 'b']
    assert renderer.render(Node(type='unknown')) == ''

    assert BlockState(['\n']).first_nonblank_from_current() is None
    store = StateStore()
    pending: list[tuple[list[Node], str]] = []
    callbacks: list[object] = []
    stream_state = StreamBlockState(
        StreamLineBuffer(['\n']),
        store=store,
        pending_inlines=pending,
        pending_inline_callbacks=callbacks,  # type: ignore[arg-type]
    )
    assert stream_state.store is store
    assert stream_state.pending_inlines is pending
    assert stream_state.pending_inline_callbacks is callbacks
    assert stream_state.first_nonblank_from_current() is None

    assert DirectiveHtmlRenderer.render(object(), HTMLRenderer(), Node(type='x'), HTMLRenderContext()) is None
    assert RootTransform.prepare(object(), Parser([]), Root(), BlockState([])) is None
    assert RootTransform.transform(object(), Parser([]), Root(), BlockState([])) is None


def test_base_rule_methods_and_wenmode_edges() -> None:
    block = BlockRule('block', r'x')
    cont = ContinueRule('continue')
    inline = InlineRule('inline', r'x')
    match = re.match('x', 'x')
    assert match is not None

    with pytest.raises(NotImplementedError):
        block.parse(Parser([]), BlockState(['x\n']), match)
    assert cont.matches('anything')
    with pytest.raises(NotImplementedError):
        cont.parse_paragraph_continuation(Parser([]), BlockState(['x\n']), [])
    assert inline.search('x') is not None
    with pytest.raises(NotImplementedError):
        inline.parse(Parser([]), 'x', match, BlockState([]))

    app = Wenmode(rules=[], renderer=HTMLRenderer(), directives=[Figure()])
    assert app.render('# Title\n') == '<p># Title</p>\n'
    app.register_rules([AtxHeading])
    assert app.render('# Title\n') == '<h1>Title</h1>\n'

    with pytest.raises(TypeError):
        Wenmode(renderer=MarkdownRenderer()).register_directive_renderer(Figure())


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


def test_heading_and_toc_helper_edges() -> None:
    root = Root(
        children=[
            Heading(depth=1, data={'id': 'existing'}, children=[Text(value='Existing')]),
            Heading(depth=2, data={}, children=[Image(alt='Alt text'), FootnoteReference(label='fn')]),
            Heading(depth=7, children=[Text(value='Skipped')]),
        ]
    )
    slugger = Slugger()

    add_heading_ids(root, slugger=slugger)

    assert root.children[0].data == {'id': 'existing'}
    assert root.children[1].data == {'id': 'alt-textfn'}
    assert (
        plain_text([Image(alt='Alt'), FootnoteReference(label='Label'), IdentifierNode(identifier='id')])
        == 'AltLabelid'
    )
    assert plain_text([Node(type='plain')]) == ''
    assert collect_toc(root, max_depth=1)[0].id == 'existing'
    assert resolve_heading_id_transform(False) == []
    assert len(resolve_heading_id_transform(True)) == 1


def test_parser_internal_edge_branches() -> None:
    Parser([LinkRule, ReferenceDefinition])
    assert list(Parser([ReferenceDefinition]).parse_iter(['[x]: /url\n'])) == []

    parser = Parser([SearchInline, LaterSearchInline, TriggerInline])
    assert parser.parse('x\n').to_ast() == {
        'type': 'root',
        'children': [{'type': 'paragraph', 'children': [{'type': 'text', 'value': 'search'}]}],
    }

    first = SearchInline()
    second = LaterSearchInline()
    parser = Parser([first, second])
    first_match = re.match('x', 'x')
    second_match = re.match('x', 'x')
    assert first_match is not None
    assert second_match is not None
    assert not parser._inline_candidate_before((0, second, second_match), (0, first, first_match))
    assert parser._inline_candidate_before((0, first, first_match), (0, second, second_match))

    with pytest.raises(RuntimeError, match='without a named group'):
        Parser([])._match_block_rule(re.match('x', 'x'))  # type: ignore[arg-type]
    unknown = re.match('(?P<missing>x)', 'x')
    assert unknown is not None
    with pytest.raises(RuntimeError, match='unknown block rule'):
        Parser([])._match_block_rule(unknown)

    list_parser = Parser([ListRule])
    list_parser.max_container_depth = 0
    assert not list_parser.is_paragraph_interrupt('- item\n', BlockState([], depth=1))
    html_parser = Parser([HtmlBlock])
    assert html_parser.is_paragraph_interrupt('<!DOCTYPE html>\n', BlockState([]))
    assert not Parser([]).is_paragraph_interrupt('# heading\n')

    assert merge_text([Text(value='a'), Text(value='b', _parse_emphasis=False)]) == [
        Text(value='a'),
        Text(value='b', _parse_emphasis=False),
    ]
    assert not contains_emphasis_marker([Text(value='*', _parse_emphasis=False), Node(type='other')])


def test_block_rule_edge_branches() -> None:
    assert parse_abbreviation_definition(BlockState(['*[HTML]:\n', '   Hyper\n', 'nope\n']), 0) == (
        2,
        'HTML',
        'Hyper',
    )
    assert parse_abbreviation_definition(BlockState(['*[HTML]:\n']), 0) == (1, 'HTML', '')
    assert parse_abbreviation_definition(BlockState(['*[broken\n']), 0) is None
    assert (
        AbbreviationDefinition().parse(
            Parser([]), BlockState(['*[broken\n']), re.match(r'.*', '*') is not None and re.match(r'.*', '*')
        )
        is None
    )
    assert replace_abbreviations(
        Text(value='HTMLX'),
        {'HTML': AbbreviationState(label='HTML', title='Hyper')},
        re.compile('HTML|MISS'),
    )[-1] == Text(value='X')
    assert replace_abbreviations(Text(value='MISS'), {}, re.compile('MISS')) == [Text(value='MISS')]
    assert (
        replace_abbreviations(
            Text(value='HTML'),
            {'HTML': AbbreviationState(label='HTML', title='Hyper')},
            re.compile('HTML'),
        )[0].type
        == 'abbreviation'
    )
    assert replace_abbreviations(Text(value='none'), {}, re.compile('MISS')) == [Text(value='none')]
    transform_abbreviations(Paragraph(children=[Node(type='child')]), {}, re.compile('MISS'))
    assert render_html(Parser([Abbreviation]), 'text\n') == '<p>text</p>\n'

    state = BlockState(['\n'])
    assert collect_description_continuation(state, []) is False
    continuation_lines: list[str] = []
    continuation_state = BlockState(['\n', '    continuation\n', 'plain\n'])
    assert collect_description_continuation(continuation_state, continuation_lines)
    assert continuation_lines == ['\n', 'continuation\n']
    assert (
        DefinitionListRule().parse_paragraph_continuation(Parser([]), BlockState([':no space\n']), ['Term\n']) is None
    )
    children: list[Node] = []
    parse_following_items(Parser([]), BlockState(['\n']), children)
    assert children == []
    assert parse_following_terms(BlockState(['\n', ': desc\n'])) is None
    assert parse_following_terms(BlockState(['\n', ' Term\n'])) is None
    assert parse_following_terms(BlockState(['Term\n', '\n'])) is None
    assert parse_following_terms(BlockState(['Term\n'])) is None

    parser = Parser([TextDirectiveRule])
    assert directive_label_children(parser, None, BlockState([])) == []
    assert parse_option_line('not an option\n') is None
    leaf_match = re.match(r'.*', '::')
    assert leaf_match is not None
    assert LeafDirectiveBlockRule().parse(Parser([]), BlockState(['::\n']), leaf_match) is None
    assert LeafDirectiveBlockRule().parse(Parser([]), BlockState(['::1bad\n']), leaf_match) is None
    assert LeafDirectiveBlockRule().parse(Parser([]), BlockState(['::bad[unterminated\n']), leaf_match) is None
    container_match = re.match(r'.*', ':::')
    assert container_match is not None
    assert ContainerDirectiveRule().parse(Parser([]), BlockState(['nope\n']), container_match) is None
    assert ContainerDirectiveRule().parse(Parser([]), BlockState([':::1bad\n']), container_match) is None
    fence_match = re.match(r'.*', '```')
    assert fence_match is not None
    assert FencedDirective().parse(Parser([]), BlockState(['```\n']), fence_match) is None
    assert FencedDirective().parse(Parser([]), BlockState(['```{note}\n']), fence_match).type == 'containerDirective'
    assert render_html(Parser([LeafDirectiveBlockRule]), '::bad trailing text\n') == '<p>::bad trailing text</p>\n'
    assert (
        render_html(Parser([ContainerDirectiveRule]), ':::bad trailing text\n:::\n')
        == '<p>:::bad trailing text\n:::</p>\n'
    )
    assert render_html(Parser([FencedDirective]), '```{bad} title\n:not option\nbody\n```\n') == (
        '<p>title</p>\n<p>:not option\nbody</p>\n'
    )

    assert render_html(Parser([FencedCode]), '`` `bad`\n') == '<p>`` `bad`</p>\n'
    assert FencedCode().parse(
        Parser([]), BlockState(['nope\n']), re.match(r'.*', 'nope') is not None and re.match(r'.*', 'nope')
    ) == Code(value='')
    assert strip_fence_indent('  code\n', 1) == ' code\n'
    assert render_html(Parser([AtxHeading]), '####### nope\n') == '<p>####### nope</p>\n'
    assert AtxHeading().parse(
        Parser([]), BlockState(['####### nope\n']), re.match(r'.*', '#') is not None and re.match(r'.*', '#')
    ) == Heading(children=[])
    assert render_html(Parser([SetextHeading]), 'a\n+\n') == '<p>a\n+</p>\n'
    assert render_html(Parser([HtmlBlock]), '<x>\n') == '&lt;x&gt;\n'
    assert render_html(Parser([HtmlBlock]), '<script>\ntext\n</script>\n') == '&lt;script&gt;\ntext\n&lt;/script&gt;\n'
    assert HtmlBlock().parse(
        Parser([]), BlockState(['<!bad\n']), re.match(r'.*', '<') is not None and re.match(r'.*', '<')
    ) == Html(value='<!bad\n')
    assert strip_indented_code('\ttoo much\n', 4) == 'too much\n'
    assert strip_indented_code('\tx\n', 2) == '  x\n'
    assert strip_indented_code('     too much\n', 4) == ' too much\n'
    assert strip_indented_code('  no\n', 4) == 'no\n'

    assert render_html(Parser([MathBlock]), '$$ x\n$$\n') == '<div class="math math-display">x\n</div>\n'
    assert MathBlockRule().parse(
        Parser([]), BlockState(['nope\n']), re.match(r'.*', 'nope') is not None and re.match(r'.*', 'nope')
    ) == Math(value='')
    assert (
        render_html(Parser([BlockSpoilerRule]), '>! one\nplain\n')
        == '<div class="spoiler">\n<p>one</p>\n</div>\n<p>plain</p>\n'
    )
    shallow_spoiler_parser = Parser([BlockSpoilerRule])
    shallow_spoiler_parser.max_container_depth = 1
    assert render_html(shallow_spoiler_parser, '>! one\n') == '<div class="spoiler">\n<p>one</p>\n</div>\n'
    shallow_state = BlockState(['>! a\n', 'plain\n'])
    assert parse_shallow_block(Parser([]), BLOCK_SPOILER_RE, shallow_state) == [Paragraph(children=[Text(value='a')])]

    table = TableRule()
    parser = Parser([TableRule])
    assert (
        table.parse(
            parser, BlockState([r'a \| b', '| --- |']), re.match('.*', 'a | b') is not None and re.match('.*', 'a | b')
        )
        is None
    )
    assert render_html(Parser([TableRule]), 'a | b\n| --- |\n') == '<p>a | b</p>\n<p>| --- |</p>\n'
    assert parse_delimiter_row('--- ---') is None
    assert parse_delimiter_row('| --- | bad |') is None
    assert parse_delimiter_row('| :--- | ---: | :---: |') == ['left', 'right', 'center']
    assert normalize_row(['a'], 3) == ['a', '', '']
    assert split_table_row('a|b') == ['a', 'b']
    assert split_table_row(r'a|b\|') == ['a', r'b\|']
    assert split_table_row('`a``b`|c') == ['`a``b`', 'c']
    assert split_table_row(r'| a \| b | `x|y` | ``z`` |') == [' a \\| b ', ' `x|y` ', ' ``z`` ']
    assert not has_unescaped_pipe(r'a \| b')


def test_list_and_task_edge_branches() -> None:
    first = MARKER_RE.match('- item')
    assert first is not None
    state = BlockState(['- item\n', 'plain\n'])
    parsed = parse_shallow_list(Parser([ListRule]), state, first, task=True)
    assert parsed.children[0].children[0] == Paragraph(children=[Text(value='item\nplain')])
    assert parse_shallow_list(Parser([]), BlockState(['plain\n']), first).children == []
    assert parse_shallow_list(Parser([]), BlockState(['- a\n', '- b\n']), first).children[0].children == [
        Paragraph(children=[Text(value='a')])
    ]
    assert parse_shallow_list(Parser([]), BlockState(['- a\n', '\n']), first).children[0].children == [
        Paragraph(children=[Text(value='a')])
    ]
    ordered = MARKER_RE.match('1. a')
    assert ordered is not None
    assert parse_shallow_list(Parser([]), BlockState(['- b\n']), ordered).children == []
    assert parse_shallow_list(Parser([]), BlockState(['2) b\n']), ordered).children == []
    bullet = MARKER_RE.match('+ a')
    assert bullet is not None
    assert parse_shallow_list(Parser([]), BlockState(['- b\n']), bullet).children == []
    assert render_html(Parser([ListRule]), '-      far\n') == '<ul>\n<li>far</li>\n</ul>\n'
    assert render_html(Parser([ListRule]), '- a\n\n  b\n\n\n- c\n') == (
        '<ul>\n<li>\n<p>a</p>\n<p>b</p>\n</li>\n<li>\n<p>c</p>\n</li>\n</ul>\n'
    )
    assert render_html(Parser([ListRule]), '- a\n\n  b\n\n\n\n- c\n').endswith('</ul>\n')
    assert ListRule().parse(
        Parser([]), BlockState(['plain\n']), re.match(r'.*', 'plain') is not None and re.match(r'.*', 'plain')
    ) == List(children=[])

    assert should_keep_blank_in_item(BlockState([], index=0), 2, 0) is False
    assert should_keep_blank_in_item(BlockState(['\n']), 2, 0) is True
    assert should_keep_blank_in_item(BlockState(['- next\n']), 2, 0) is True
    assert blank_belongs_to_item([], BlockState([]), 2, 0) is True
    assert blank_belongs_to_item([], BlockState(['\n']), 2, 0) is True
    assert has_open_fence(['```\n', 'code\n'])
    assert not has_open_fence(['```\n', '```\n'])

    item_without_paragraph = ListItem(children=[Text(value='[x] done')])
    apply_task_list_marker(item_without_paragraph)
    assert item_without_paragraph.checked is None
    empty_paragraph = ListItem(children=[Paragraph(children=[])])
    apply_task_list_marker(empty_paragraph)
    assert empty_paragraph.checked is None
    item = ListItem(children=[Paragraph(children=[Text(value='[x] ')])])
    apply_task_list_marker(item)
    assert item.checked is True
    assert item.children == [Paragraph(children=[])]


def test_directive_parsing_helpers_and_invalid_inline_directives(monkeypatch: pytest.MonkeyPatch) -> None:
    assert parse_directive_head('1bad') is None
    assert parse_directive_head('name[unterminated') is None
    assert parse_directive_head('name{unterminated') is None
    assert find_balanced(r'[a\[b]', 0, '[', ']') == 5
    assert find_balanced('[a[b]c]', 0, '[', ']') == 6
    assert parse_attributes("#id .one..two key='a\\'b' empty =bad") == {
        'id': 'id',
        'key': "a'b",
        'empty': '',
        'class': 'one two',
    }
    assert parse_attributes('=bad') == {}
    assert tokenize_attributes('  ') == []
    assert tokenize_attributes('a  b') == ['a', 'b']
    monkeypatch.setattr(directives_module, 'tokenize_attributes', lambda text: ['   '])
    assert directives_module.parse_attributes('ignored') == {}
    attributes: dict[str, str] = {}
    classes: list[str] = []
    parse_shortcuts('#.class', attributes, classes)
    assert attributes == {}
    assert classes == ['class']
    parse_shortcuts('x#id', attributes, classes)
    assert attributes == {}

    parser = Parser([TextDirectiveInlineRule])
    assert render_html(parser, ':1\n') == '<p>:1</p>\n'
    text_directive_match = re.match(r':', ':1')
    assert text_directive_match is not None
    assert TextDirectiveInlineRule().parse(Parser([]), ':1', text_directive_match, BlockState([])) == (None, 0)
    role_match = re.match(r'\{', '{1}')
    assert role_match is not None
    assert Role().parse(Parser([]), '{1}', role_match, BlockState([])) == (None, 0)
    assert parse_role('nope') is None
    assert parse_role('{bad') is None
    assert parse_role('{bad name}`x`') is None
    assert parse_role('{role}x') is None
    assert parse_role('{role}`x') is None


def test_reference_and_footnote_edge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    assert FootnoteRule().parse(Parser([]), '[^x]', re.match(r'\[\^x]', '[^x]')) == (None, 0)  # type: ignore[arg-type]
    assert render_html(Parser([Footnote]), '[^]: bad\n') == '<p>[^]: bad</p>\n'
    footnote_match = re.match(r'.*', '[^x]: note')
    assert footnote_match is not None
    monkeypatch.setattr(footnotes_module, 'normalize_label', lambda label: '')
    assert FootnoteDefinitionRule().parse(Parser([]), BlockState(['[^x]: note\n']), footnote_match) is None

    state = BlockState(['\n'])
    assert has_later_continuation(state) is False
    state = BlockState(['rest\n'])
    assert collect_definition_lines(state, '') == []
    assert collect_definition_lines(BlockState(['def\n', 'x\n']), '') == []
    assert strip_footnote_indent('\tx\n', 2) == 'x\n'
    assert strip_footnote_indent('x\n', 2) == 'x\n'
    first = FootnoteDefinition(identifier='one', children=[])
    duplicate = FootnoteDefinition(identifier='one', children=[Paragraph(children=[Text(value='two')])])
    assert collect_footnote_definitions(Root(children=[first, duplicate])) == {'one': first}
    assert has_later_continuation(BlockState(['def\n', '\n', '  later\n']))

    assert parse_reference(BlockState(['[^x]: /url\n']), 0) is None
    assert parse_reference(BlockState(['[x]:\n', '\n']), 0) is None
    assert parse_reference(BlockState(['[x]: <unterminated\n']), 0) is None
    assert parse_reference(BlockState(['[x]: <line\nbreak>\n']), 0) is None
    assert parse_reference(BlockState(['[x]: <url>title\n']), 0) is None
    assert parse_reference(BlockState(['[x]: /url "unterminated\n']), 0) is None
    assert parse_reference(BlockState(['[x]: /url "title" extra\n']), 0) is None
    assert parse_reference(BlockState(['[x]: /url\n', '"title"\n']), 0) == (2, 'x', '/url', 'title')
    assert parse_reference_destination('<unterminated') == (None, '<unterminated')
    assert parse_reference_destination('<bad\nurl>') == (None, '<bad\nurl>')
    assert parse_reference_destination('') == (None, '')
    assert parse_reference_title('') is None
    assert parse_reference_title('plain') is None
    assert parse_multiline_reference_title('"title', BlockState(['\n']), 0) == (None, 0)
    assert parse_multiline_reference_title('"title', BlockState(['continued"\n']), 0) == (('title\ncontinued', ''), 1)
    assert parse_multiline_label_reference(BlockState(['nope\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[^x\n', ']: /url\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', 'x]: \n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', 'x]: /url "unterminated\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', 'x]: /url "title" extra\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', '\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[x\n', ']: /url "title"\n']), 0) == (
        2,
        'x\n',
        '/url',
        'title',
    )


def test_inline_link_and_math_edge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = Parser([LinkRule, ImageRule])
    assert render_html(parser, '![alt\n') == '<p>![alt</p>\n'
    assert render_html(parser, '![[link](/url)](/image)\n') == '<p><img src="/image" alt="link" /></p>\n'
    assert render_html(Parser([LinkRule(references=False)]), '[x][ref]\n') == '<p>[x][ref]</p>\n'
    assert normalize_optional_text(None) is None
    assert normalize_optional_text('a\nb') == 'a\nb'
    assert parse_link_or_image(Parser([]), '[x]', 0, False, None, references=True) is None
    assert closing_bracket_cache(None) is None
    assert parse_direct_destination('[x]', 0) is None
    assert parse_direct_destination('(<bad\\url>)', 0) is None
    assert parse_direct_destination('(/url "title"', 0) is None
    assert parse_destination('<bad\\url>', 0) == (None, 0)
    assert parse_destination('/a\\)b)', 0) == ('/a\\)b', 5)
    assert parse_title('"a\\"b"', 0) == ('a"b', 6)
    assert parse_title("'title'", 0) == ('title', 7)
    assert parse_title('(title)', 0) == ('title', 7)
    assert parse_title('plain', 0) is None
    assert parse_title('"unterminated', 0) is None
    assert build_closing_bracket_map(r'[a \[ `]` <x[y]> [b]]') == {1: 20, 13: 14, 18: 19}
    assert build_closing_bracket_map('`[x]` [y]') == {7: 8}
    assert build_closing_bracket_map('`unterminated [x]') == {15: 16}
    assert find_closing_bracket_uncached(r'a \] b', 0) is None
    assert find_closing_bracket_uncached('`x` <http://example.com> ]', 0) == 25
    assert find_closing_bracket_uncached('<not-angle]', 0) == 10
    assert find_closing_bracket_uncached('`unterminated] [x]', 0) == 13
    assert find_closing_bracket_uncached('[x]', 0) is None
    assert find_closing_bracket('[]', 1, None) == 1
    assert find_closing_bracket('a]', 0, {}) == 1
    assert closing_bracket_map('[x]', None) == {1: 2}
    assert invalid_reference_label(r'a\z')
    assert not invalid_reference_label(r'a\[\]\\')
    assert link_plain_text(
        [InlineCode(value='code'), Image(alt='alt'), Break(), Paragraph(children=[Text(value='p')])]
    ) == ('codealt\np')
    assert link_plain_text([Node(type='plain')]) == ''
    assert find_code_span_end('`unterminated', 0) is None

    assert render_html(Parser([InlineMath]), '$ $\n') == '<p>$ $</p>\n'
    inline_math_match = re.match(r'\$', '$ $')
    assert inline_math_match is not None
    assert InlineMathRule().parse(Parser([]), '$ $', inline_math_match, BlockState([])) == (None, 0)
    monkeypatch.setattr(math_module, 'find_closing_dollar', lambda text, start: 1)
    assert InlineMathRule().parse(Parser([]), '$x', inline_math_match, BlockState([])) == (None, 0)
    assert find_closing_dollar('$a\n$', 1) is None
    assert find_closing_dollar('$a $2 b$', 1) == 7


def test_ruby_strikethrough_autolink_and_emphasis_edge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    parser = Parser([RubyRule])
    ruby = parse_ruby_segments('[漢(kan)]')
    assert parse_ruby_link(parser, '[漢(kan)]', 8, Node(type='ruby'), BlockState([])) is None  # type: ignore[arg-type]
    assert parse_ruby_link(Parser([RubyRule, LinkRule]), '[漢(kan)](', 8, Node(type='ruby'), BlockState([])) is None  # type: ignore[arg-type]
    assert parse_ruby_link(Parser([RubyRule, LinkRule]), '[漢(kan)]x', 8, Node(type='ruby'), BlockState([])) is None  # type: ignore[arg-type]
    assert parse_ruby_link(Parser([RubyRule, LinkRule]), '[漢(kan)][', 8, Node(type='ruby'), BlockState([])) is None  # type: ignore[arg-type]
    assert parse_ruby_link(Parser([RubyRule, LinkRule]), '[漢(kan)][]', 8, Node(type='ruby'), BlockState([])) is None  # type: ignore[arg-type]
    assert (
        parse_ruby_link(Parser([RubyRule, LinkRule]), '[漢(kan)][missing]', 8, Node(type='ruby'), BlockState([]))
        is None
    )  # type: ignore[arg-type]
    assert ruby == [{'base': '漢', 'text': 'kan'}]

    assert render_html(Parser([Strikethrough]), '~~~~\n') == '<p>~~~~</p>\n'
    strike_match = re.match(r'~~', '~~')
    assert strike_match is not None
    monkeypatch.setattr(strikethrough_module, 'find_closing_marker', lambda text, marker, start: start)
    assert Strikethrough().parse(Parser([]), '~~x', strike_match, BlockState([])) == (None, 0)
    assert find_closing_marker(r'~~a\~~b~~', '~~', 2) == 7

    autolink = ExtendedAutolinkRule()
    match = re.match(r'.*', '...')
    assert match is not None
    assert autolink.parse(Parser([]), '...', match) == (None, 0)
    assert autolink.search('ahttp://example.com') is None
    assert autolink.search('x@example.com') is not None

    assert Emphasis().parse(Parser([]), '*', re.match(r'\*', '*')) == (None, 0)  # type: ignore[arg-type]
    assert parse_emphasis_sequence([Text(value='**a*')]) == [
        Text(value='*'),
        EmphasisNode(children=[Text(value='a')]),
    ]
    strong_disabled_parts: list[Node] = [Text(value='*'), Text(value='a'), Text(value='**')]
    process_delimiters(
        strong_disabled_parts,
        [Delimiter(0, '*', 2, True, False), Delimiter(2, '*', 2, False, True)],
    )
    assert strong_disabled_parts == [Text(value=''), EmphasisNode(children=[Text(value='a')]), Text(value='*')]
    empty_parts: list[Node] = [Text(value='*'), Text(value='*')]
    process_delimiters(empty_parts, [Delimiter(0, '*', 1, True, False), Delimiter(1, '*', 1, False, True)])
    assert empty_parts == [Text(value='*'), Text(value='*')]
    non_text_parts: list[Node] = [Node(type='opener'), Text(value='a'), Text(value='*')]
    monkeypatch.setattr(
        emphasis_module, 'text_value', lambda node: '*' if node.type == 'opener' else getattr(node, 'value', '')
    )
    process_delimiters(non_text_parts, [Delimiter(0, '*', 1, True, False), Delimiter(2, '*', 1, False, True)])
    assert non_text_parts == [Node(type='opener'), Text(value='a'), Text(value='*')]


def test_html_end_pattern_defensive_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    class NoTagPattern:
        def match(self, line: str) -> None:
            return None

    monkeypatch.setattr(html_block_module, 'HTML_OPEN_TAG_RE', NoTagPattern())
    assert html_block_module.html_end_pattern('<script>') is None
    assert find_closing_delimiter('`*` a*', '*', 0) == 5
    assert find_closing_delimiter('`*`', '*', 0) == -1
    assert not can_open('a_b', 1, 1, '_')
    assert not can_open('* ', 0, 1, '*')
    assert not can_open('a*.', 1, 1, '*')
    assert not can_close('a_b', 1, 1, '_')
    assert not can_close(' *', 1, 1, '*')
    assert not can_close('.*a', 1, 1, '*')
    assert is_inside_code_span('`code *` *', 6)
    assert not is_inside_code_span('`unterminated *', 14)

    parts: list[Node] = [Text(value='*'), Text(value='')]
    process_delimiters(parts, [Delimiter(0, '*', 1, True, False), Delimiter(1, '*', 1, False, True)])
    assert parts == [Text(value='*'), Text(value='')]
