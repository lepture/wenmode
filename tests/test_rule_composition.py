from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from tests.helpers import max_type_depth, text_values
from wenmode import HTMLRenderer, Wenmode
from wenmode.nodes import Node, Parent
from wenmode.presets import github
from wenmode.rules import (
    AtxHeading,
    Blockquote,
    Emphasis,
    Footnote,
    HtmlBlock,
    Image,
    Link,
    List,
    SetextHeading,
    ThematicBreak,
)
from wenmode.rules.base import BlockRule


@dataclass
class CustomRecursiveBlock(Parent):
    type: str = 'customRecursiveBlock'


class RecursiveBlockRule(BlockRule):
    name = 'recursive_block'
    pattern = r'@@[A-Z]'

    def parse(self, parser: Any, state: Any, match: re.Match[str]) -> Node | None:
        marker = state.line.rstrip('\r\n')[2:]
        if len(marker) != 1:
            return None

        state.advance()
        closer = f'@@/{marker}'
        source = state.source.collect()
        lines: list[str] = []
        while not state.done:
            line = state.line
            if line.rstrip('\r\n') == closer:
                state.advance()
                break
            lines.append(line)
            source.add(state.index, 0, line)
            state.advance()
        return CustomRecursiveBlock(children=parser.parse_blocks(''.join(lines), state, source=source.map()))


def _recursive_block_markdown(depth: int) -> str:
    markers = [chr(ord('A') + index) for index in range(depth)]
    return (
        ''.join(f'@@{marker}\n' for marker in markers)
        + 'deepest source\n'
        + ''.join(f'@@/{marker}\n' for marker in reversed(markers))
    )


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


def test_custom_block_rule_parse_blocks_respects_max_container_depth() -> None:
    app = Wenmode([RecursiveBlockRule])
    app.parser.max_container_depth = 2

    ast = app.parse(_recursive_block_markdown(8)).to_ast()

    assert max_type_depth(ast, CustomRecursiveBlock.type) <= app.parser.max_container_depth
    assert any('deepest source' in value for value in text_values(ast))


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


def test_angle_link_destination_accepts_backslash_escapes() -> None:
    app = Wenmode([Link])

    assert app.render('[link](<foo\\*bar>)\n') == '<p><a href="foo*bar">link</a></p>\n'
    assert app.render('[link](<foo\\>bar>)\n') == '<p><a href="foo%3Ebar">link</a></p>\n'
    assert app.render('[link](<foo\\<bar>)\n') == '<p><a href="foo%3Cbar">link</a></p>\n'


def test_angle_link_destination_rejects_unescaped_angle_opener() -> None:
    app = Wenmode([Link])

    assert app.render('[link](<foo<bar>)\n') == '<p>[link](&lt;foo&lt;bar&gt;)</p>\n'


def test_bare_link_destination_only_escapes_punctuation() -> None:
    app = Wenmode([Link])

    assert app.render('[link](foo\\ bar)\n') == '<p>[link](foo\\ bar)</p>\n'
    assert app.render('[link](foo\\*bar)\n') == '<p><a href="foo*bar">link</a></p>\n'
    assert app.render('[link](foo\\bar)\n') == '<p><a href="foo%5Cbar">link</a></p>\n'


def test_reference_uri_normalization_requires_semicolon_for_character_references() -> None:
    app = Wenmode([Link])

    assert app.render('[x]: https://example.com/search?tag=red&section=all\n\n[x]\n') == (
        '<p><a href="https://example.com/search?tag=red&amp;section=all">x</a></p>\n'
    )


def test_angle_reference_destination_accepts_backslash_escapes() -> None:
    app = Wenmode([Link])

    assert app.render('[x]: <a\\*b>\n\n[x]\n') == '<p><a href="a*b">x</a></p>\n'
    assert app.render('[x]: <a\\>b>\n\n[x]\n') == '<p><a href="a%3Eb">x</a></p>\n'
    assert app.render('[x]: <a\\<b>\n\n[x]\n') == '<p><a href="a%3Cb">x</a></p>\n'


def test_angle_reference_destination_rejects_unescaped_angle_opener() -> None:
    app = Wenmode([Link])

    assert app.render('[x]: <a<b>\n\n[x]\n') == '<p>[x]: &lt;a&lt;b&gt;</p>\n<p>[x]</p>\n'


def test_bare_reference_destination_only_escapes_punctuation() -> None:
    app = Wenmode([Link])

    assert app.render('[x]: foo\\ bar\n\n[x]\n') == '<p>[x]: foo\\ bar</p>\n<p>[x]</p>\n'
    assert app.render('[x]: foo\\*bar\n\n[x]\n') == '<p><a href="foo*bar">x</a></p>\n'
    assert app.render('[x]: foo\\bar\n\n[x]\n') == '<p><a href="foo%5Cbar">x</a></p>\n'


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
