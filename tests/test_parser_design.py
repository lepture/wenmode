from __future__ import annotations

import re
from io import StringIO

import pytest

from wenmode import HTMLRenderer, Parser, StreamingUnsupportedError, Wenmode
from wenmode.nodes import Node, Paragraph, Root, Text
from wenmode.presets import commonmark, github, streaming
from wenmode.rules import (
    AtxHeading,
    Blockquote,
    BlockRule,
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
from wenmode.state import BlockState, SourceMap, StateKey

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


def test_parser_dynamic_rule_registration_updates_rule_dependencies() -> None:
    parser = Parser([])

    parser.register_rule(Link)

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'


def test_custom_extension_state_uses_state_store() -> None:
    app = Wenmode([Glossary, Blockquote])

    assert 'term_definition' in app.parser.rules

    root = app.parse('> @term[nested]: Nested\n\n@term[root]: Root\n\ntext\n')
    assert root.data == {'terms': {'nested': 'Nested', 'root': 'Root'}}
    assert not hasattr(BlockState([]), 'references')
    assert not hasattr(BlockState([]), 'footnotes')
    assert not hasattr(BlockState([]), 'abbreviations')

    assert app.parse('text\n').data == {'terms': {}}


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
    assert isinstance(app.parser.rules, dict)


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

    assert app.parser.root_transforms == []
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
    wenmode = Wenmode(streaming)
    markdown = '# Title\n\nA [link](/url) and ~~old~~ text.\n\n| A | B |\n| --- | --- |\n| x | y |\n\n- one\n- two\n'

    assert ''.join(wenmode.stream(markdown)) == wenmode.render(markdown)
    assert ''.join(wenmode.stream(StringIO(markdown))) == wenmode.render(markdown)
    assert ''.join(wenmode.stream(lines(markdown))) == wenmode.render(markdown)


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
    with pytest.raises(StreamingUnsupportedError):
        next(Wenmode(commonmark).stream('[x]\n\n[x]: /url\n'))

    with pytest.raises(StreamingUnsupportedError):
        next(Wenmode(github).stream('a[^one]\n\n[^one]: note\n'))

    with pytest.raises(StreamingUnsupportedError):
        next(Wenmode([Footnote]).stream('a[^one]\n\n[^one]: note\n'))


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
