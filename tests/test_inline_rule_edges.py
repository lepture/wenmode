from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import Parser
from wenmode.nodes import Break, Image, InlineCode, Node, Paragraph, Text
from wenmode.nodes import Emphasis as EmphasisNode
from wenmode.rules import Emphasis, Strikethrough
from wenmode.rules import ExtendedAutolink as ExtendedAutolinkRule
from wenmode.rules import Image as ImageRule
from wenmode.rules import InlineMath as InlineMathRule
from wenmode.rules import Link as LinkRule
from wenmode.rules import Ruby as RubyRule
from wenmode.rules.inlines import emphasis as emphasis_module
from wenmode.rules.inlines import math as math_module
from wenmode.rules.inlines import strikethrough as strikethrough_module
from wenmode.rules.inlines.emphasis import (
    Delimiter,
    can_close,
    can_open,
    find_closing_delimiter,
    is_inside_code_span,
    parse_emphasis_sequence,
    process_delimiters,
)
from wenmode.rules.inlines.extended_autolink import trim_mailto_or_xmpp, trim_xmpp
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
from wenmode.rules.inlines.link import plain_text as link_plain_text
from wenmode.rules.inlines.math import find_closing_dollar
from wenmode.rules.inlines.ruby import parse_ruby_link, parse_ruby_segments
from wenmode.rules.inlines.strikethrough import find_closing_marker
from wenmode.state import BlockState

from ._edge_helpers import (
    render_html,
)

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class InlineRuleEdgeExample(TypedDict):
    name: str
    rules: list[str]
    markdown: str
    html: str


def load_inline_rule_edge_examples() -> list[InlineRuleEdgeExample]:
    return json.loads((FIXTURES_DIR / 'inline_rule_edges.json').read_text())


def inline_edge_rule(name: str):
    if name == 'link_no_references':
        return LinkRule(references=False)
    return {
        'image': ImageRule,
        'inline_math': InlineMathRule,
        'link': LinkRule,
        'strikethrough': Strikethrough,
    }[name]


@pytest.mark.parametrize(
    'example',
    load_inline_rule_edge_examples(),
    ids=lambda example: example['name'],
)
def test_inline_rule_edge_examples(example: InlineRuleEdgeExample) -> None:
    parser = Parser([inline_edge_rule(name) for name in example['rules']])

    assert render_html(parser, example['markdown']) == example['html']


def test_inline_link_and_math_edge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
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
    assert autolink.search_email('xx@example.com', 1) is None
    assert autolink.search_email('x@example.com-', 0) is None
    assert autolink.search('x@example.com') is not None
    assert trim_mailto_or_xmpp('https://example.com') == 'https://example.com'
    assert trim_xmpp('xmpp:x@example.com-') == ''
    assert trim_xmpp('xmpp:not-email/path') == ''

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


def test_emphasis_helper_edges() -> None:
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
