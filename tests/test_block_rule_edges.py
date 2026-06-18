from __future__ import annotations

import re

import pytest

from wenmode import Parser
from wenmode.nodes import Code, Heading, Html, List, ListItem, Math, Node, Paragraph, Text
from wenmode.rules import Abbreviation, AtxHeading, FencedCode, FencedDirective, HtmlBlock, SetextHeading
from wenmode.rules import BlockSpoiler as BlockSpoilerRule
from wenmode.rules import ContainerDirective as ContainerDirectiveRule
from wenmode.rules import DefinitionList as DefinitionListRule
from wenmode.rules import LeafDirective as LeafDirectiveBlockRule
from wenmode.rules import List as ListRule
from wenmode.rules import MathBlock as MathBlockRule
from wenmode.rules import Table as TableRule
from wenmode.rules import TextDirective as TextDirectiveRule
from wenmode.rules.blocks import html as html_block_module
from wenmode.rules.blocks.abbr import (
    AbbreviationDefinition,
    AbbreviationState,
    parse_abbreviation_definition,
    replace_abbreviations,
    transform_abbreviations,
)
from wenmode.rules.blocks.definition_list import (
    collect_description_continuation,
    parse_following_items,
    parse_following_terms,
)
from wenmode.rules.blocks.directive import directive_label_children, parse_option_line
from wenmode.rules.blocks.fenced_code import strip_fence_indent
from wenmode.rules.blocks.indented_code import strip_indent as strip_indented_code
from wenmode.rules.blocks.list import (
    MARKER_RE,
    apply_task_list_marker,
    blank_belongs_to_item,
    has_open_fence,
    parse_shallow_list,
    should_keep_blank_in_item,
)
from wenmode.rules.blocks.spoiler import BLOCK_SPOILER_RE
from wenmode.rules.blocks.table import has_unescaped_pipe, normalize_row, parse_delimiter_row, split_table_row
from wenmode.rules.blocks.util import parse_shallow_block
from wenmode.rules.inlines.emphasis import (
    Delimiter,
    can_close,
    can_open,
    find_closing_delimiter,
    is_inside_code_span,
    process_delimiters,
)
from wenmode.state import BlockState

from ._edge_helpers import (
    render_html,
)


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

    assert render_html(Parser([MathBlockRule]), '$$ x\n$$\n') == '<div class="math math-display">x\n</div>\n'
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
    assert render_html(Parser([TableRule]), 'a | b\n| --- |\n') == '<p>a | b\n| --- |</p>\n'
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


def test_html_end_pattern_defensive_branch(monkeypatch: pytest.MonkeyPatch) -> None:
    class NoTagPattern:
        def match(self, line: str) -> None:
            return None

    monkeypatch.setattr(html_block_module, 'HTML_OPEN_TAG_RE', NoTagPattern())
    assert html_block_module.html_end_pattern('<script>') is None
