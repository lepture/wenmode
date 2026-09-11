from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from wenmode import Parser
from wenmode.nodes import Literal, Node, Parent, Text
from wenmode.plugins import InlineDelimited, InlineLiteral
from wenmode.rules import InlineCandidate
from wenmode.state import BlockState


@dataclass
class DelimitedNode(Parent):
    type: str = 'delimited'


@dataclass
class LiteralDelimitedNode(Literal):
    type: str = 'literalDelimited'


def paragraph_children(rule: InlineDelimited | InlineLiteral, source: str) -> list[Node]:
    root = Parser([rule]).parse(source + '\n')
    paragraph = root.children[0]
    assert isinstance(paragraph, Parent)
    return paragraph.children


def delimited_text(rule: InlineDelimited | InlineLiteral, source: str) -> str | None:
    children = paragraph_children(rule, source)
    for child in children:
        if isinstance(child, LiteralDelimitedNode):
            return child.value
        if isinstance(child, DelimitedNode):
            return ''.join(grandchild.value for grandchild in child.children if isinstance(grandchild, Text))
    return None


class GeneralInlineDelimited(InlineDelimited):
    """Test rule that bypasses the optimized parsing strategies."""

    def __init__(self, **options: Any) -> None:
        super().__init__(**options)
        self._parse_impl = self._parse_general


def test_multichar_inline_literal_ignores_partial_opener_matches() -> None:
    class CountingLiteral(InlineLiteral):
        parse_calls = 0

        def parse(
            self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
        ) -> tuple[Node | None, int]:
            self.parse_calls += 1
            return super().parse(parser, text, candidate, state)

    rule = CountingLiteral(name='counting_literal', node=LiteralDelimitedNode, opener='{%', closer='%}')
    parser = Parser([rule])

    parser.parse('{' * 1000 + '\n')
    assert rule.parse_calls == 0

    parser.parse('{%value%}\n')
    assert rule.parse_calls == 1


def test_declarative_inline_rules_validate_delimiters_and_node_shapes() -> None:
    with pytest.raises(ValueError, match='opener must not be empty'):
        InlineDelimited(name='empty_opener', node=DelimitedNode, opener='', closer='==')
    with pytest.raises(ValueError, match='closer must not be empty'):
        InlineLiteral(name='empty_closer', node=LiteralDelimitedNode, opener='$', closer='')
    with pytest.raises(TypeError, match="'parent_required' requires a Parent node"):
        InlineDelimited(name='parent_required', node=LiteralDelimitedNode, opener='==', closer='==')
    with pytest.raises(TypeError, match="'literal_required' requires a Literal node"):
        InlineLiteral(name='literal_required', node=DelimitedNode, opener='$', closer='$')


@pytest.mark.parametrize('strip_content', [False, True])
def test_inline_delimited_allows_adjacent_closer_character_when_longer_runs_are_allowed(strip_content: bool) -> None:
    rule = InlineDelimited(
        name='delimited',
        node=DelimitedNode,
        opener='>!',
        closer='!<',
        allow_newline=False,
        reject_opening_whitespace=False,
        reject_closing_whitespace=False,
        reject_longer_run=False,
        strip_content=strip_content,
    )

    assert delimited_text(rule, '>!bang!!<') == 'bang!'


@pytest.mark.parametrize(
    ('options', 'sources'),
    [
        (
            {'opener': '==', 'closer': '=='},
            [
                'plain text',
                '==value==',
                '==a *nested* value==',
                '====',
                '===value===',
                r'\==escaped==',
                r'==escaped closer\==',
                '== leading==',
                '==trailing ==',
                '==a\nb==',
            ],
        ),
        (
            {
                'opener': '>!',
                'closer': '!<',
                'allow_newline': False,
                'reject_opening_whitespace': False,
                'reject_closing_whitespace': False,
                'reject_longer_run': False,
                'strip_content': True,
            },
            [
                'plain text',
                '>!value!<',
                '>!  value  !<',
                '>!!<',
                '>!   !<',
                '>!bang!!<',
                r'\>!escaped!<',
                r'>!escaped closer\!<',
                '>!first!<!<',
                '>!a\nb!<',
            ],
        ),
    ],
)
def test_optimized_inline_delimited_strategies_match_general_parser(
    options: dict[str, Any], sources: list[str]
) -> None:
    optimized = InlineDelimited(name='optimized', node=DelimitedNode, **options)
    general = GeneralInlineDelimited(name='general', node=DelimitedNode, **options)

    for source in sources:
        optimized_ast = Parser([optimized]).parse(source + '\n').to_ast()
        general_ast = Parser([general]).parse(source + '\n').to_ast()
        assert optimized_ast == general_ast


@pytest.mark.parametrize(
    ('options', 'source', 'expected'),
    [
        ({}, '==value==', 'value'),
        ({}, r'\==value==', None),
        ({'escape': False}, r'\==value==', 'value'),
        ({}, '====', None),
        ({'reject_empty': False, 'reject_longer_run': False}, '====', ''),
        ({}, '== value==', None),
        ({'reject_opening_whitespace': False}, '== value==', ' value'),
        ({}, '==value ==', None),
        ({'reject_closing_whitespace': False}, '==value ==', 'value '),
        ({'allow_newline': False}, '==a\nb==', None),
        ({'reject_longer_run': True}, '===value===', None),
        ({'reject_longer_run': False}, '===value===', '=value'),
        (
            {'strip_content': True, 'reject_opening_whitespace': False, 'reject_closing_whitespace': False},
            '==  value  ==',
            'value',
        ),
    ],
)
def test_inline_delimited_options(options: dict[str, bool], source: str, expected: str | None) -> None:
    rule = InlineDelimited(name='delimited', node=DelimitedNode, opener='==', closer='==', **options)

    assert delimited_text(rule, source) == expected


@pytest.mark.parametrize(
    ('options', 'source', 'expected'),
    [
        ({}, '$value$', 'value'),
        ({}, r'\$value$', None),
        ({'escape': False}, r'\$value$', 'value'),
        ({}, '$$', None),
        ({'reject_empty': False}, '$$', ''),
        ({}, '$ value$', None),
        ({'reject_opening_whitespace': False}, '$ value$', ' value'),
        ({}, '$value $', None),
        ({'reject_closing_whitespace': False}, '$value $', 'value '),
        ({'allow_newline': False}, '$a\nb$', None),
        ({'allow_newline': True}, '$a\nb$', 'a\nb'),
        ({'reject_longer_run': True}, '$$value$$', None),
        ({'reject_adjacent_delimiter': True}, '$$value$$', None),
        ({'reject_closing_before_digit': True}, '$value$5', None),
        (
            {'strip_content': True, 'reject_opening_whitespace': False, 'reject_closing_whitespace': False},
            '$  value  $',
            'value',
        ),
    ],
)
def test_inline_literal_options(options: dict[str, bool], source: str, expected: str | None) -> None:
    rule = InlineLiteral(name='literal', node=LiteralDelimitedNode, opener='$', closer='$', **options)

    assert delimited_text(rule, source) == expected
