from __future__ import annotations

import re
from collections.abc import Mapping
from io import StringIO

import pytest

from wenmode import HTMLRenderer, Parser, StreamingUnsupportedError, Wenmode
from wenmode.nodes import Node, Paragraph, Parent, Root, Text
from wenmode.presets import commonmark, github, streaming
from wenmode.rules import (
    AtxHeading,
    Blockquote,
    BlockRule,
    ContinueRule,
    Emphasis,
    Footnote,
    HtmlBlock,
    Image,
    InlineCode,
    InlineRule,
    Link,
    List,
    RootTransform,
    Rule,
    SetextHeading,
    Table,
    ThematicBreak,
)
from wenmode.state import BlockState, SourceMap, StateKey, StateStore

TERMS = StateKey('tests.terms', lambda: {})
TERM_RE = re.compile(r'^[ \t]{0,3}@term\[(?P<label>[^\]]+)]:[ \t]*(?P<title>.*)$')


class Glossary(Rule):
    def __init__(self) -> None:
        super().__init__('glossary')
        self.root_transforms = [GlossaryTransform()]


class TermDefinition(BlockRule):
    def __init__(self) -> None:
        super().__init__('term_definition', r'[ \t]{0,3}@term\[')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        term = TERM_RE.match(state.line.rstrip('\r\n'))
        if term is None:
            return None

        state.store.get(TERMS)[term.group('label')] = term.group('title')
        state.advance()
        return None


class GlossaryTransform(RootTransform):
    name = 'glossary'
    required_rules = [TermDefinition]

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        root.data = {'terms': dict(state.store.get(TERMS))}


class BoxNode(Parent):
    def __init__(self, children: list[Node]) -> None:
        super().__init__('box', children=children)


def render(parser: Parser, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


def lines(markdown: str):
    yield from markdown.splitlines(keepends=True)


def parse_inlines(parser: Parser, markdown: str) -> list[Node]:
    return parser.parse_inlines(markdown, BlockState([]))


def test_rule_base_state_is_instance_local() -> None:
    first = Rule('first')
    second = Rule('second')

    first.root_transforms.append(GlossaryTransform())

    assert second.root_transforms == []


def test_state_store_sets_scalar_values() -> None:
    key = StateKey('tests.scalar', lambda: 0)
    store = StateStore()

    store.set(key, store.get(key) + 1)

    assert store.get(key) == 1


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


def test_parser_reuses_reference_state_per_parse() -> None:
    app = Wenmode([Link])

    assert app.render('[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'
    assert app.render('[x]\n') == '<p>[x]</p>\n'
    assert not hasattr(app.parser, 'references')
    assert not hasattr(app.parser, '_state_stack')


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


def test_custom_extension_state_uses_state_store() -> None:
    app = Wenmode([Glossary, Blockquote])

    assert 'term_definition' in app.parser.rules

    root = app.parse('> @term[nested]: Nested\n\n@term[root]: Root\n\ntext\n')
    assert root.data == {'terms': {'nested': 'Nested', 'root': 'Root'}}
    assert not hasattr(BlockState([]), 'references')
    assert not hasattr(BlockState([]), 'footnotes')
    assert not hasattr(BlockState([]), 'abbreviations')

    assert app.parse('text\n').data == {'terms': {}}


def test_deferred_inline_callbacks_and_state_store_are_per_parse() -> None:
    values = StateKey('tests.deferred_values', lambda: [])

    class DeferredRule(Rule):
        def __init__(self) -> None:
            super().__init__('deferred_rule')
            self.root_transforms = [DeferredTransform()]

    class DeferredTransform(RootTransform):
        name = 'deferred_transform'
        defer_inlines = True

        def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
            def record_resolved_text() -> None:
                paragraph = root.children[0]
                first_child = getattr(paragraph, 'children', [])[0]
                state.store.get(values).append(getattr(first_child, 'value', ''))

            state.pending_inline_callbacks.append(record_resolved_text)

        def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
            root.data = {
                'values': list(state.store.get(values)),
                'pending_inlines': len(state.pending_inlines),
                'pending_callbacks': len(state.pending_inline_callbacks),
            }

    app = Wenmode([DeferredRule])

    assert app.parse('first\n').data == {
        'values': ['first'],
        'pending_inlines': 0,
        'pending_callbacks': 0,
    }
    assert app.parse('second\n').data == {
        'values': ['second'],
        'pending_inlines': 0,
        'pending_callbacks': 0,
    }


def test_nested_block_and_inline_source_maps_share_parent_state() -> None:
    class BoxRule(BlockRule):
        name = 'box'
        pattern = r'[ \t]{0,3}::box[ \t]*$'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            state.advance()
            lines: list[str] = []
            source = state.source.collect()
            while not state.done:
                if re.match(r'[ \t]{0,3}::[ \t]*$', state.line):
                    state.advance()
                    break
                source.add(state.index, 0, state.line)
                lines.append(state.line)
                state.advance()
            return BoxNode(parser.parse_blocks(''.join(lines), state, source=source.map()))

    app = Wenmode([BoxRule, AtxHeading, InlineCode], positions=True)
    root = app.parse('lead\n\n::box\n# Title\n\nText `code`.\n::\n')

    box = root.to_ast()['children'][1]

    assert box['type'] == 'box'
    assert box['position'] == {
        'start': {'line': 3, 'column': 1, 'offset': 6},
        'end': {'line': 8, 'column': 1, 'offset': 37},
    }
    assert box['children'][0]['position'] == {
        'start': {'line': 4, 'column': 1, 'offset': 12},
        'end': {'line': 5, 'column': 1, 'offset': 20},
    }
    assert box['children'][0]['children'][0]['position'] == {
        'start': {'line': 4, 'column': 3, 'offset': 14},
        'end': {'line': 4, 'column': 8, 'offset': 19},
    }
    assert box['children'][1]['children'][1] == {
        'type': 'inlineCode',
        'position': {
            'start': {'line': 6, 'column': 6, 'offset': 26},
            'end': {'line': 6, 'column': 12, 'offset': 32},
        },
        'value': 'code',
    }


def test_parser_replaces_dynamic_rules_by_name() -> None:
    parser = Parser([AtxHeading])

    parser.register_rule(AtxHeading)

    assert render(parser, '# Title\n') == '<h1>Title</h1>\n'


def test_parser_accepts_synchronous_text_streams() -> None:
    app = Wenmode(github)
    markdown = '# Title\n\nA [link][x] and a note[^one].\n\n[x]: /url\n[^one]: note\n'
    expected = app.render(markdown)

    assert app.render(StringIO(markdown)) == expected
    assert app.render(markdown.splitlines(keepends=True)) == expected
    assert app.render(lines(markdown)) == expected


def test_iterable_source_positions_support_carriage_return_lines() -> None:
    ast = Wenmode(positions=True).parse(iter(['# a\r', '# b\r'])).to_ast()

    assert [child['position']['start'] for child in ast['children']] == [
        {'line': 1, 'column': 1, 'offset': 0},
        {'line': 2, 'column': 1, 'offset': 4},
    ]
    assert ast['position']['end'] == {'line': 3, 'column': 1, 'offset': 8}


def test_stream_reference_definition_can_affect_earlier_blocks() -> None:
    app = Wenmode([Link])
    markdown = '[x]\n\n[x]: /url "ti\ntle"\n'

    assert app.render(lines(markdown)) == '<p><a href="/url" title="ti\ntle">x</a></p>\n'


def test_stream_table_lookahead() -> None:
    app = Wenmode([Table])
    markdown = '| a | b |\n| --- | --- |\n| c | d |\n'

    assert app.render(lines(markdown)) == app.render(markdown)


def test_stream_footnote_continuation_lookahead() -> None:
    app = Wenmode([Footnote])
    markdown = '[^one]: first\n\n  second\n\nA note[^one]\n'

    assert app.render(lines(markdown)) == app.render(markdown)


def test_parser_binds_footnote_definitions_to_root() -> None:
    app = Wenmode([Footnote])
    root = app.parse('a[^one]\n\n[^one]: note\n')

    assert root.footnote_definitions is not None
    assert list(root.footnote_definitions) == ['one']
    assert root.footnote_definitions['one'].label == 'one'


def test_parser_skips_root_footnote_definitions_without_footnote_rule() -> None:
    app = Wenmode([AtxHeading])
    root = app.parse('# Title\n\n[^one]: note\n')

    assert root.footnote_definitions is None


def test_stream_list_blank_line_lookahead() -> None:
    app = Wenmode([List])
    markdown = '- a\n\n  b\n- c\n'

    assert app.render(lines(markdown)) == app.render(markdown)


def test_reference_definitions_are_plain_text_without_reference_consumers() -> None:
    app = Wenmode([AtxHeading])

    assert app.render('[x]: /url\n\n[x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n'
    assert isinstance(app.parser.rules, Mapping)


def test_fence_like_text_is_not_protected_without_fenced_code_rule() -> None:
    app = Wenmode([Link])

    assert app.render('```\n\n[x]: /url\n\n[x]\n') == '<p>```</p>\n<p><a href="/url">x</a></p>\n'


def test_blockquote_depth_is_limited() -> None:
    app = Wenmode([Blockquote])
    app.parser.max_container_depth = 8

    assert 'a' in app.render('> ' * 1000 + 'a\n')


def test_list_depth_is_limited() -> None:
    app = Wenmode([List])
    app.parser.max_container_depth = 8

    markdown = ''.join('  ' * index + '- a\n' for index in range(64))
    assert 'a' in app.render(markdown)


def test_deep_list_fast_path_at_depth_limit() -> None:
    app = Wenmode([List])
    app.parser.max_container_depth = 1

    markdown = ''.join('  ' * index + '- a\n' for index in range(1000))
    assert 'a' in app.render(markdown)


def test_emphasis_rule_enables_strong_and_emphasis() -> None:
    app = Wenmode([Emphasis])

    assert app.render('*a* **b**\n') == '<p><em>a</em> <strong>b</strong></p>\n'


def test_setext_heading_rule_owns_paragraph_continuation() -> None:
    assert Wenmode([SetextHeading]).render('a\n-\n') == '<h2>a</h2>\n'
    assert Wenmode([]).render('a\n-\n') == '<p>a\n-</p>\n'


def test_thematic_break_rule_does_not_depend_on_list_order() -> None:
    app = Wenmode([List, ThematicBreak])

    assert app.render('- - -\n') == '<hr />\n'


def test_image_keeps_reference_definitions_enabled() -> None:
    app = Wenmode([Image])

    assert app.render('[x]: /img.png\n\n![x]\n') == '<p><img src="/img.png" alt="x" /></p>\n'


def test_link_and_image_share_one_reference_transform() -> None:
    app = Wenmode([Link, Image])

    assert [transform.name for transform in app.parser.root_transforms] == ['reference']
    assert app.render('[x]: /url\n\n[x] and ![x]\n') == ('<p><a href="/url">x</a> and <img src="/url" alt="x" /></p>\n')


def test_uri_normalization_requires_semicolon_for_character_references() -> None:
    app = Wenmode([Link, Image])

    assert app.render('[link](https://example.com/search?tag=red&section=all)\n') == (
        '<p><a href="https://example.com/search?tag=red&amp;section=all">link</a></p>\n'
    )
    assert app.render('[link](https://example.com/search?tag=red&sect;ion=all)\n') == (
        '<p><a href="https://example.com/search?tag=red%C2%A7ion=all">link</a></p>\n'
    )
    assert app.render('[&quotidian](&quotidian) ![&quotidian](&quotidian)\n') == (
        '<p><a href="&amp;quotidian">&amp;quotidian</a> <img src="&amp;quotidian" alt="&amp;quotidian" /></p>\n'
    )


def test_reference_uri_normalization_requires_semicolon_for_character_references() -> None:
    app = Wenmode([Link])

    assert app.render('[x]: https://example.com/search?tag=red&section=all\n\n[x]\n') == (
        '<p><a href="https://example.com/search?tag=red&amp;section=all">x</a></p>\n'
    )


def test_html_block_preserves_nested_pre_across_blank_lines() -> None:
    renderer = HTMLRenderer(escape=False)
    app = Wenmode([HtmlBlock], renderer=renderer)

    assert app.render('<div>\n<pre>\nbefore\n\nafter\n</pre>\n</div>\n') == (
        '<div>\n<pre>\nbefore\n\nafter\n</pre>\n</div>\n'
    )


def test_link_and_image_can_disable_references() -> None:
    app = Wenmode([Image(references=False), Link(references=False)])

    assert app.parser.root_transforms == ()
    assert app.render('[x](/url) and ![alt](/img.png)\n') == (
        '<p><a href="/url">x</a> and <img src="/img.png" alt="alt" /></p>\n'
    )
    assert app.render('[x]: /url\n\n[x]\n\n![x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n<p>![x]</p>\n'
    assert 'reference_definition' not in app.parser.rules


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


def test_inline_sources_are_state_local() -> None:
    other_state = BlockState([])
    observations: list[tuple[int, int, bool]] = []

    class ProbeSource(InlineRule):
        name = 'probe_source'
        pattern = r'!'
        trigger_chars = '!'

        def parse(
            self, parser: Parser, text: str, match: re.Match[str], state: BlockState
        ) -> tuple[Node | None, int]:
            current_source = parser.inline_source(text, state, match.start(), match.end())
            other_source = parser.inline_source(text, other_state, match.start(), match.end())
            assert current_source is not None
            observations.append(
                (
                    current_source.source_offset(0),
                    current_source.source_offset(1),
                    other_source is None,
                )
            )
            return Text(value='!'), match.end()

    parser = Parser([ProbeSource], positions=True)
    state = BlockState([])

    parser.parse_inlines('!', state, source=SourceMap.contiguous('!', 42))

    assert observations == [(42, 43, True)]
    assert state.inline_sources == []
    assert other_state.inline_sources == []


def test_streaming_preset_disables_references() -> None:
    app = Wenmode(streaming)

    assert 'reference_definition' not in app.parser.rules
    assert app.render('[x](/url) and ![alt](/img.png)\n') == (
        '<p><a href="/url">x</a> and <img src="/img.png" alt="alt" /></p>\n'
    )
    assert app.render('[x]: /url\n\n[x]\n\n![x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n<p>![x]</p>\n'


def test_wenmode_stream_matches_full_render_for_streaming_preset() -> None:
    wen = Wenmode(streaming)
    markdown = '# Title\n\nA [link](/url) and ~~old~~ text.\n\n| A | B |\n| --- | --- |\n| x | y |\n\n- one\n- two\n'

    assert ''.join(wen.stream(markdown)) == wen.render(markdown)
    assert ''.join(wen.stream(StringIO(markdown))) == wen.render(markdown)
    assert ''.join(wen.stream(lines(markdown))) == wen.render(markdown)


def test_streaming_preset_supports_table_and_strikethrough() -> None:
    html = Wenmode(streaming).render('| A | B |\n| --- | --- |\nx | ~~old~~\n')

    assert '<table>' in html
    assert '<td><del>old</del></td>' in html


def test_wenmode_stream_does_not_read_entire_input_before_first_chunk() -> None:
    consumed = 0

    def chunks():
        nonlocal consumed
        for line in ['# Title\n', '\n', 'Second paragraph.\n']:
            consumed += 1
            yield line

    stream = Wenmode(streaming).stream(chunks())

    assert next(stream) == '<h1>Title</h1>\n'
    assert consumed == 1


def test_wenmode_stream_rejects_unsupported_rules() -> None:
    with pytest.raises(StreamingUnsupportedError, match='reference'):
        next(Wenmode(commonmark).stream('[x]\n\n[x]: /url\n'))

    with pytest.raises(StreamingUnsupportedError, match='footnote, reference'):
        next(Wenmode(github).stream('a[^one]\n\n[^one]: note\n'))

    with pytest.raises(StreamingUnsupportedError, match='footnote'):
        next(Wenmode([Footnote]).stream('a[^one]\n\n[^one]: note\n'))


def test_parser_and_wenmode_report_streaming_support() -> None:
    streamable = Wenmode(streaming)
    full_document = Wenmode(github)

    assert streamable.supports_streaming is True
    assert streamable.parser.supports_streaming is True
    assert streamable.streaming_blockers() == []
    assert streamable.parser.streaming_blockers() == []

    assert full_document.supports_streaming is False
    assert full_document.parser.supports_streaming is False
    assert full_document.streaming_blockers() == ['footnote', 'reference']
    assert full_document.parser.streaming_blockers() == ['footnote', 'reference']


def test_parser_reuses_footnote_state_per_parse() -> None:
    app = Wenmode([Footnote])

    assert 'data-footnote-ref' in app.render('[^one]: note\n\na[^one]\n')
    assert app.render('a[^one]\n') == '<p>a[^one]</p>\n'


def test_footnote_definitions_are_plain_text_without_footnote_rule() -> None:
    app = Wenmode([Link])

    assert app.render('[^one]: note\n\n[^one]\n') == '<p>[^one]: note</p>\n<p>[^one]</p>\n'


def test_github_preset_enables_footnotes_with_links() -> None:
    app = Wenmode(github)

    html = app.render('[link](/url) and a[^one]\n\n[^one]: note\n')

    assert '<a href="/url">link</a>' in html
    assert 'data-footnote-ref' in html


def test_footnote_rule_does_not_depend_on_link_order() -> None:
    app = Wenmode([Link, Footnote])

    assert 'data-footnote-ref' in app.render('a[^one]\n\n[^one]: note\n')
