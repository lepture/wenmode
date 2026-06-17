from __future__ import annotations

from io import StringIO

from wenmode import HTMLRenderer, Parser, github
from wenmode.rules import (
    AtxHeading,
    Blockquote,
    Emphasis,
    FencedCode,
    Footnote,
    Image,
    Link,
    List,
    SetextHeading,
    Table,
    ThematicBreak,
)


def render(parser: Parser, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


def lines(markdown: str):
    yield from markdown.splitlines(keepends=True)


def test_parser_reuses_reference_state_per_parse() -> None:
    parser = Parser([Link])

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'
    assert render(parser, '[x]\n') == '<p>[x]</p>\n'
    assert not hasattr(parser, 'references')
    assert not hasattr(parser, '_state_stack')


def test_parser_registers_rules_dynamically() -> None:
    parser = Parser([])

    assert render(parser, '# Title\n') == '<p># Title</p>\n'

    parser.register_rule(AtxHeading)

    assert render(parser, '# Title\n') == '<h1>Title</h1>\n'


def test_parser_dynamic_rule_registration_updates_rule_dependencies() -> None:
    parser = Parser([])

    parser.register_rule(Link)

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'


def test_parser_replaces_dynamic_rules_by_name() -> None:
    parser = Parser([AtxHeading])

    parser.register_rule(AtxHeading)

    assert render(parser, '# Title\n') == '<h1>Title</h1>\n'


def test_parser_accepts_synchronous_text_streams() -> None:
    parser = Parser(github)
    markdown = '# Title\n\nA [link][x] and a note[^one].\n\n[x]: /url\n[^one]: note\n'
    expected = HTMLRenderer().render(parser.parse(markdown))

    assert HTMLRenderer().render(parser.parse(StringIO(markdown))) == expected
    assert HTMLRenderer().render(parser.parse(markdown.splitlines(keepends=True))) == expected
    assert HTMLRenderer().render(parser.parse(lines(markdown))) == expected


def test_stream_reference_definition_can_affect_earlier_blocks() -> None:
    parser = Parser([Link])
    markdown = '[x]\n\n[x]: /url "ti\ntle"\n'

    assert HTMLRenderer().render(parser.parse(lines(markdown))) == '<p><a href="/url" title="ti\ntle">x</a></p>\n'


def test_stream_table_lookahead() -> None:
    parser = Parser([Table])
    markdown = '| a | b |\n| --- | --- |\n| c | d |\n'

    assert HTMLRenderer().render(parser.parse(lines(markdown))) == HTMLRenderer().render(parser.parse(markdown))


def test_stream_footnote_continuation_lookahead() -> None:
    parser = Parser([Footnote])
    markdown = '[^one]: first\n\n  second\n\nA note[^one]\n'

    assert HTMLRenderer().render(parser.parse(lines(markdown))) == HTMLRenderer().render(parser.parse(markdown))


def test_parser_binds_footnote_definitions_to_root() -> None:
    parser = Parser([Footnote])
    root = parser.parse('a[^one]\n\n[^one]: note\n')

    assert root.footnote_definitions is not None
    assert list(root.footnote_definitions) == ['one']
    assert root.footnote_definitions['one'].label == 'one'


def test_parser_skips_root_footnote_definitions_without_footnote_rule() -> None:
    parser = Parser([AtxHeading])
    root = parser.parse('# Title\n\n[^one]: note\n')

    assert root.footnote_definitions is None


def test_stream_list_blank_line_lookahead() -> None:
    parser = Parser([List])
    markdown = '- a\n\n  b\n- c\n'

    assert HTMLRenderer().render(parser.parse(lines(markdown))) == HTMLRenderer().render(parser.parse(markdown))


def test_reference_definitions_are_plain_text_without_reference_consumers() -> None:
    parser = Parser([AtxHeading])

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n'
    assert isinstance(parser.rules, dict)


def test_fence_like_text_is_not_protected_without_fenced_code_rule() -> None:
    parser = Parser([Link])

    assert render(parser, '```\n\n[x]: /url\n\n[x]\n') == '<p>```</p>\n<p><a href="/url">x</a></p>\n'


def test_blockquote_depth_is_limited() -> None:
    parser = Parser([Blockquote])
    parser.max_container_depth = 8

    assert 'a' in render(parser, '> ' * 1000 + 'a\n')


def test_list_depth_is_limited() -> None:
    parser = Parser([List])
    parser.max_container_depth = 8

    markdown = ''.join('  ' * index + '- a\n' for index in range(64))
    assert 'a' in render(parser, markdown)


def test_deep_list_fast_path_at_depth_limit() -> None:
    parser = Parser([List])
    parser.max_container_depth = 1

    markdown = ''.join('  ' * index + '- a\n' for index in range(1000))
    assert 'a' in render(parser, markdown)


def test_emphasis_rule_enables_strong_and_emphasis() -> None:
    parser = Parser([Emphasis])

    assert render(parser, '*a* **b**\n') == '<p><em>a</em> <strong>b</strong></p>\n'


def test_setext_heading_rule_owns_paragraph_continuation() -> None:
    assert render(Parser([SetextHeading]), 'a\n-\n') == '<h2>a</h2>\n'
    assert render(Parser([]), 'a\n-\n') == '<p>a\n-</p>\n'


def test_thematic_break_rule_does_not_depend_on_list_order() -> None:
    parser = Parser([List, ThematicBreak])

    assert render(parser, '- - -\n') == '<hr />\n'


def test_image_keeps_reference_definitions_enabled() -> None:
    parser = Parser([Image])

    assert render(parser, '[x]: /img.png\n\n![x]\n') == '<p><img src="/img.png" alt="x" /></p>\n'


def test_parser_reuses_footnote_state_per_parse() -> None:
    parser = Parser([Footnote])

    assert 'data-footnote-ref' in render(parser, '[^one]: note\n\na[^one]\n')
    assert render(parser, 'a[^one]\n') == '<p>a[^one]</p>\n'


def test_footnote_definitions_are_plain_text_without_footnote_rule() -> None:
    parser = Parser([Link])

    assert render(parser, '[^one]: note\n\n[^one]\n') == '<p>[^one]: note</p>\n<p>[^one]</p>\n'


def test_github_preset_enables_footnotes_with_links() -> None:
    parser = Parser(github)

    html = render(parser, '[link](/url) and a[^one]\n\n[^one]: note\n')

    assert '<a href="/url">link</a>' in html
    assert 'data-footnote-ref' in html


def test_footnote_rule_does_not_depend_on_link_order() -> None:
    parser = Parser([Link, Footnote])

    assert 'data-footnote-ref' in render(parser, 'a[^one]\n\n[^one]: note\n')
