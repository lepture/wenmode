from __future__ import annotations

import re
from collections.abc import Mapping

import pytest

from wenmode import HTMLRenderer, Parser, Wenmode
from wenmode.nodes import Node, Paragraph, Text
from wenmode.rules import (
    AtxHeading,
    BlockRule,
    ContinueRule,
    Footnote,
    InlineCode,
    InlineRule,
    Link,
    RootTransform,
    Rule,
)
from wenmode.state import BlockState


def render(parser: Parser, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


def parse_inlines(parser: Parser, markdown: str) -> list[Node]:
    return parser.parse_inlines(markdown, BlockState([]))


def test_rule_base_state_is_instance_local() -> None:
    first = Rule('first')
    second = Rule('second')

    first.root_transforms.append(RootTransform())

    assert second.root_transforms == []


def test_inline_rule_compiles_pattern_on_init() -> None:
    rule = InlineCode()

    assert rule.compiled.pattern == rule.pattern


def test_rule_subclasses_can_define_identity_as_class_attributes() -> None:
    class BangBlock(BlockRule):
        name = 'bang_block'
        pattern = r'[ \t]{0,3}!!$'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            state.advance()
            return Paragraph(children=[Text(value='bang')])

    class BangInline(InlineRule):
        name = 'bang_inline'
        pattern = r'!!'
        trigger_chars = '!'

        def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
            return Text(value='inline'), match.end()

    app = Wenmode([BangBlock, BangInline])

    assert app.render('!!\n\nhi !!\n') == '<p>bang</p>\n<p>hi inline</p>\n'


def test_block_rule_returning_node_must_advance_state() -> None:
    class NonProgressingBlock(BlockRule):
        name = 'non_progressing_block'
        pattern = r'!!'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            return Paragraph(children=[])

    parser = Parser([NonProgressingBlock])

    with pytest.raises(RuntimeError, match=r"non_progressing_block.*state did not advance"):
        parser.parse('!!\n')


def test_block_rule_cannot_move_state_backwards() -> None:
    class BackwardsBlock(BlockRule):
        name = 'backwards_block'
        pattern = r'!!'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            state.advance(-1)
            return None

    parser = Parser([BackwardsBlock])

    with pytest.raises(RuntimeError, match=r"backwards_block.*state backwards"):
        parser.parse('!!\n')


def test_continuation_rule_returning_node_must_advance_state() -> None:
    class NonProgressingContinuation(ContinueRule):
        name = 'non_progressing_continuation'

        def matches(self, line: str) -> bool:
            return line.startswith('!!')

        def parse_paragraph_continuation(
            self, parser: Parser, state: BlockState, lines: list[str]
        ) -> Node | None:
            return Paragraph(children=[])

    parser = Parser([NonProgressingContinuation])

    with pytest.raises(RuntimeError, match=r"non_progressing_continuation.*state did not advance"):
        parser.parse('text\n!!\n')


def test_continuation_rule_decline_must_not_advance_state() -> None:
    class ForwardDecliningContinuation(ContinueRule):
        name = 'forward_declining_continuation'

        def matches(self, line: str) -> bool:
            return line.startswith('!!')

        def parse_paragraph_continuation(
            self, parser: Parser, state: BlockState, lines: list[str]
        ) -> Node | None:
            state.advance()
            return None

    parser = Parser([ForwardDecliningContinuation])

    with pytest.raises(RuntimeError, match=r"forward_declining_continuation.*declining continuation changed state"):
        parser.parse('text\n!!\ntail\n')


def test_continuation_rule_decline_must_not_move_state_backwards() -> None:
    class BackwardDecliningContinuation(ContinueRule):
        name = 'backward_declining_continuation'

        def __init__(self) -> None:
            super().__init__()
            self.moved = False

        def matches(self, line: str) -> bool:
            return line.startswith('!!')

        def parse_paragraph_continuation(
            self, parser: Parser, state: BlockState, lines: list[str]
        ) -> Node | None:
            if not self.moved:
                self.moved = True
                state.advance(-1)
            return None

    parser = Parser([BackwardDecliningContinuation])

    with pytest.raises(RuntimeError, match=r"backward_declining_continuation.*declining continuation changed state"):
        parser.parse('text\n!!\n')


def test_continuation_rule_can_decline_without_advancing() -> None:
    class DecliningContinuation(ContinueRule):
        name = 'declining_continuation'

        def matches(self, line: str) -> bool:
            return line.startswith('!!')

        def parse_paragraph_continuation(
            self, parser: Parser, state: BlockState, lines: list[str]
        ) -> Node | None:
            return None

    assert render(Parser([DecliningContinuation]), 'text\n!!\n') == '<p>text\n!!</p>\n'


def test_block_rule_can_decline_without_advancing() -> None:
    class DecliningBlock(BlockRule):
        name = 'declining_block'
        pattern = r'!!'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            return None

    assert render(Parser([DecliningBlock]), '!!\n') == '<p>!!</p>\n'


def test_block_rule_can_consume_without_returning_node() -> None:
    class ConsumingBlock(BlockRule):
        name = 'consuming_block'
        pattern = r'!!'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            state.advance()
            return None

    assert render(Parser([ConsumingBlock]), '!!\ntext\n') == '<p>text</p>\n'


def test_parser_registers_rules_dynamically() -> None:
    parser = Parser([])

    assert render(parser, '# Title\n') == '<p># Title</p>\n'

    parser.register_rule(AtxHeading)

    assert render(parser, '# Title\n') == '<h1>Title</h1>\n'


def test_parser_rule_collections_are_read_only() -> None:
    parser = Parser([AtxHeading, InlineCode, Link])

    assert isinstance(parser.rules, Mapping)
    with pytest.raises(TypeError):
        parser.rules['heading'] = AtxHeading()
    with pytest.raises(TypeError):
        del parser.rules['atx_heading']

    for rules in (parser.block_rules, parser.inline_rules, parser.root_transforms):
        with pytest.raises(AttributeError):
            rules.append(AtxHeading())


def test_parser_registration_rebuilds_read_only_rule_views() -> None:
    parser = Parser([])

    parser.register_rule(AtxHeading)

    assert list(parser.rules) == ['atx_heading']
    assert [rule.name for rule in parser.block_rules] == ['atx_heading']
    assert parser.inline_rules == ()
    assert parser.root_transforms == ()

    parser.register_rules([InlineCode, Link])

    assert list(parser.rules) == ['atx_heading', 'inline_code', 'link', 'reference_definition']
    assert [rule.name for rule in parser.block_rules] == ['atx_heading', 'reference_definition']
    assert [rule.name for rule in parser.inline_rules] == ['inline_code', 'link']
    assert [transform.name for transform in parser.root_transforms] == ['reference']


def test_parser_dynamic_rule_registration_updates_rule_dependencies() -> None:
    parser = Parser([])

    parser.register_rule(Link)

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'


def test_parser_rebuilds_inline_dispatch_when_rule_is_replaced() -> None:
    class AtToken(InlineRule):
        name = 'token'
        pattern = r'@a'
        trigger_chars = '@'

        def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
            return Text(value='at'), match.end()

    class BangToken(InlineRule):
        name = 'token'
        pattern = r'!b'
        trigger_chars = '!'

        def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
            return Text(value='bang'), match.end()

    parser = Parser([AtToken])

    assert render(parser, '@a !b\n') == '<p>at !b</p>\n'

    parser.register_rule(BangToken)

    assert [rule.name for rule in parser.inline_rules] == ['token']
    assert render(parser, '@a !b\n') == '<p>@a bang</p>\n'


def test_inline_dispatch_uses_rule_order_for_equal_offset_candidates() -> None:
    class TriggeredAt(InlineRule):
        name = 'triggered_at'
        pattern = r'@'
        trigger_chars = '@'

        def parse(
            self, parser: Parser, text: str, match: re.Match[str], state: BlockState
        ) -> tuple[Node | None, int]:
            return Text(value='triggered'), match.end()

    class SearchedAt(InlineRule):
        name = 'searched_at'
        pattern = r'@'

        def parse(
            self, parser: Parser, text: str, match: re.Match[str], state: BlockState
        ) -> tuple[Node | None, int]:
            return Text(value='searched'), match.end()

    triggered_first = parse_inlines(Parser([TriggeredAt, SearchedAt]), '@')
    searched_first = parse_inlines(Parser([SearchedAt, TriggeredAt]), '@')

    assert [node.to_ast() for node in triggered_first] == [{'type': 'text', 'value': 'triggered'}]
    assert [node.to_ast() for node in searched_first] == [{'type': 'text', 'value': 'searched'}]


def test_parser_replaces_dynamic_rules_by_name() -> None:
    parser = Parser([AtxHeading])

    parser.register_rule(AtxHeading)

    assert render(parser, '# Title\n') == '<h1>Title</h1>\n'


def test_parse_inlines_with_explicit_state_handles_link_brackets() -> None:
    assert [node.to_ast() for node in parse_inlines(Parser([Link]), '[a \\] b](/url)')] == [
        {
            'type': 'link',
            'children': [{'type': 'text', 'value': 'a \\] b'}],
            'url': '/url',
        }
    ]
    assert [node.to_ast() for node in parse_inlines(Parser([Link, InlineCode]), '[a `[b]` c](/url)')] == [
        {
            'type': 'link',
            'children': [
                {'type': 'text', 'value': 'a '},
                {'type': 'inlineCode', 'value': '[b]'},
                {'type': 'text', 'value': ' c'},
            ],
            'url': '/url',
        }
    ]
    assert [node.to_ast() for node in parse_inlines(Parser([Link]), '[a <https://e.test/[x]> c](/url)')] == [
        {
            'type': 'link',
            'children': [{'type': 'text', 'value': 'a <https://e.test/[x]> c'}],
            'url': '/url',
        }
    ]
    assert [node.to_ast() for node in parse_inlines(Parser([Link]), '[a [b]](/url)')] == [
        {
            'type': 'link',
            'children': [{'type': 'text', 'value': 'a [b]'}],
            'url': '/url',
        }
    ]
    assert [node.to_ast() for node in parse_inlines(Parser([Link]), '[a [b](/url')] == [
        {'type': 'text', 'value': '[a [b](/url'}
    ]


def test_parse_inlines_with_fresh_state_leaves_footnote_reference_text() -> None:
    assert [node.to_ast() for node in parse_inlines(Parser([Footnote]), '[^x]')] == [{'type': 'text', 'value': '[^x]'}]
