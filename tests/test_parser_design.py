from __future__ import annotations

from wenmode import HTMLRenderer, Wenmode
from wenmode.rules import AtxHeading, Blockquote, Emphasis, FencedCode, Image, Link, List


def render(parser: Wenmode, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


def test_parser_reuses_reference_state_per_parse() -> None:
    parser = Wenmode([Link])

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'
    assert render(parser, '[x]\n') == '<p>[x]</p>\n'
    assert not hasattr(parser, 'references')
    assert not hasattr(parser, '_state_stack')


def test_reference_definitions_are_plain_text_without_reference_consumers() -> None:
    parser = Wenmode([AtxHeading])

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n'


def test_fence_like_text_is_not_protected_without_fenced_code_rule() -> None:
    parser = Wenmode([Link])

    assert render(parser, '```\n\n[x]: /url\n\n[x]\n') == '<p>```</p>\n<p><a href="/url">x</a></p>\n'


def test_blockquote_depth_is_limited() -> None:
    parser = Wenmode([Blockquote])
    parser.max_container_depth = 8

    assert 'a' in render(parser, '> ' * 1000 + 'a\n')


def test_list_depth_is_limited() -> None:
    parser = Wenmode([List])
    parser.max_container_depth = 8

    markdown = ''.join('  ' * index + '- a\n' for index in range(64))
    assert 'a' in render(parser, markdown)


def test_deep_list_fast_path_at_depth_limit() -> None:
    parser = Wenmode([List])
    parser.max_container_depth = 1

    markdown = ''.join('  ' * index + '- a\n' for index in range(1000))
    assert 'a' in render(parser, markdown)


def test_emphasis_rule_enables_strong_and_emphasis() -> None:
    parser = Wenmode([Emphasis])

    assert render(parser, '*a* **b**\n') == '<p><em>a</em> <strong>b</strong></p>\n'


def test_image_keeps_reference_definitions_enabled() -> None:
    parser = Wenmode([Image])

    assert render(parser, '[x]: /img.png\n\n![x]\n') == '<p><img src="/img.png" alt="x" /></p>\n'
