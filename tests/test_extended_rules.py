from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import HTMLRenderer, MarkdownRenderer, Parser
from wenmode.presets import commonmark, github
from wenmode.rules import (
    Abbreviation,
    BackslashEscape,
    Blockquote,
    BlockSpoiler,
    DefinitionList,
    Emphasis,
    Footnote,
    InlineCode,
    InlineMath,
    InlineSpoiler,
    Insert,
    Link,
    Mark,
    MathBlock,
    Ruby,
    Strikethrough,
    Subscript,
    Superscript,
)

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class ExtendedRuleExample(TypedDict):
    name: str
    markdown: str
    html: str


def load_examples(name: str) -> list[ExtendedRuleExample]:
    return json.loads((FIXTURES_DIR / name).read_text())


def render(parser: Parser, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


@pytest.mark.parametrize(
    'example',
    load_examples('footnotes.json'),
    ids=lambda example: example['name'],
)
def test_footnote_examples(example: ExtendedRuleExample) -> None:
    parser = Parser([Footnote, Emphasis, Blockquote, Link])

    assert render(parser, example['markdown']) == example['html']


@pytest.mark.parametrize(
    'example',
    load_examples('math.json'),
    ids=lambda example: example['name'],
)
def test_math_examples(example: ExtendedRuleExample) -> None:
    parser = Parser([MathBlock, InlineCode, InlineMath])

    assert render(parser, example['markdown']) == example['html']


def test_math_is_not_enabled_by_presets() -> None:
    markdown = '$x$\n\n$$\nx\n$$\n'

    assert render(Parser(commonmark), markdown) == '<p>$x$</p>\n<p>$$\nx\n$$</p>\n'
    assert render(Parser(github), markdown) == '<p>$x$</p>\n<p>$$\nx\n$$</p>\n'


def test_mark_rule() -> None:
    parser = Parser([Mark, BackslashEscape, Emphasis])
    root = parser.parse('==marked *text*== and ==mark \\== equal==\n')

    assert HTMLRenderer().render(root) == '<p><mark>marked <em>text</em></mark> and <mark>mark == equal</mark></p>\n'
    assert MarkdownRenderer().render(root) == '==marked *text*== and ==mark == equal==\n'


def test_mark_requires_tight_delimiters() -> None:
    parser = Parser([Mark])

    assert render(parser, '== no mark==\n') == '<p>== no mark==</p>\n'
    assert render(parser, '==no mark ==\n') == '<p>==no mark ==</p>\n'
    assert render(parser, '===no mark===\n') == '<p>===no mark===</p>\n'


def test_insert_rule() -> None:
    parser = Parser([Insert, BackslashEscape, Emphasis])
    root = parser.parse('^^insert *text*^^ and ^^insert \\^^ caret^^\n')

    assert HTMLRenderer().render(root) == '<p><ins>insert <em>text</em></ins> and <ins>insert ^^ caret</ins></p>\n'
    assert MarkdownRenderer().render(root) == '^^insert *text*^^ and ^^insert ^^ caret^^\n'


def test_insert_requires_tight_delimiters() -> None:
    parser = Parser([Insert])

    assert render(parser, '^^ no insert^^\n') == '<p>^^ no insert^^</p>\n'
    assert render(parser, '^^no insert ^^\n') == '<p>^^no insert ^^</p>\n'
    assert render(parser, '^^^no insert^^^\n') == '<p>^^^no insert^^^</p>\n'


def test_superscript_rule() -> None:
    parser = Parser([Superscript, BackslashEscape, Emphasis])
    root = parser.parse('2^10^ and ^with\\ space^ and ^escaped\\^caret^\n')

    assert (
        HTMLRenderer().render(root) == '<p>2<sup>10</sup> and <sup>with space</sup> and <sup>escaped^caret</sup></p>\n'
    )
    assert MarkdownRenderer().render(root) == '2^10^ and ^with\\ space^ and ^escaped\\^caret^\n'


def test_superscript_does_not_allow_plain_spaces() -> None:
    parser = Parser([Superscript])

    assert render(parser, '^no script^\n') == '<p>^no script^</p>\n'


def test_subscript_rule() -> None:
    parser = Parser([Subscript, Strikethrough, BackslashEscape, Emphasis])
    root = parser.parse('H~2~O and ~with\\ space~ and ~escaped\\~tilde~ and ~~delete~~\n')

    assert (
        HTMLRenderer().render(root)
        == '<p>H<sub>2</sub>O and <sub>with space</sub> and <sub>escaped~tilde</sub> and <del>delete</del></p>\n'
    )
    assert MarkdownRenderer().render(root) == 'H~2~O and ~with\\ space~ and ~escaped\\~tilde~ and ~~delete~~\n'


def test_subscript_does_not_allow_plain_spaces() -> None:
    parser = Parser([Subscript])

    assert render(parser, '~no script~\n') == '<p>~no script~</p>\n'


def test_ruby_rule() -> None:
    parser = Parser([Ruby])
    root = parser.parse('[汉字(hàn zì)] and [汉(hàn)字(zì)]\n')

    assert (
        HTMLRenderer().render(root)
        == '<p><ruby>汉字<rt>hàn zì</rt></ruby> and <ruby>汉<rt>hàn</rt>字<rt>zì</rt></ruby></p>\n'
    )
    assert MarkdownRenderer().render(root) == '[汉字(hàn zì)] and [汉(hàn)字(zì)]\n'


def test_ruby_link_rule() -> None:
    parser = Parser([Ruby, Link])
    root = parser.parse('[漢字(kanji)](/ruby "Ruby") and [漢字(kanji)][term]\n\n[term]: /term\n')

    assert (
        HTMLRenderer().render(root) == '<p><a href="/ruby" title="Ruby"><ruby>漢字<rt>kanji</rt></ruby></a> and '
        '<a href="/term"><ruby>漢字<rt>kanji</rt></ruby></a></p>\n'
    )


def test_inline_spoiler_rule() -> None:
    parser = Parser([InlineSpoiler, Emphasis])
    root = parser.parse('A >! hidden *thing* !< appears.\n')

    assert HTMLRenderer().render(root) == '<p>A <span class="spoiler">hidden <em>thing</em></span> appears.</p>\n'
    assert MarkdownRenderer().render(root) == 'A >! hidden *thing* !< appears\\.\n'


def test_block_spoiler_rule() -> None:
    parser = Parser([BlockSpoiler, Emphasis])
    root = parser.parse('>! hidden *thing*\n>!\n>! second paragraph\n')

    assert (
        HTMLRenderer().render(root)
        == '<div class="spoiler">\n<p>hidden <em>thing</em></p>\n<p>second paragraph</p>\n</div>\n'
    )
    assert MarkdownRenderer().render(root) == '>! hidden *thing*\n>!\n>! second paragraph\n'


def test_abbreviation_rule() -> None:
    parser = Parser([Abbreviation])
    root = parser.parse(
        'The HTML spec is maintained by W3C.\n\n*[HTML]: Hyper Text Markup Language\n*[W3C]: Consortium\n'
    )

    assert (
        HTMLRenderer().render(root)
        == '<p>The <abbr title="Hyper Text Markup Language">HTML</abbr> spec is maintained by '
        '<abbr title="Consortium">W3C</abbr>.</p>\n'
    )
    assert MarkdownRenderer().render(root) == 'The HTML spec is maintained by W3C\\.\n'


def test_definition_list_rule() -> None:
    parser = Parser([DefinitionList, Emphasis])
    root = parser.parse('Apple\n: Pomaceous *fruit*\n\nOrange\n: Citrus fruit\n')

    assert (
        HTMLRenderer().render(root) == '<dl>\n<dt>Apple</dt>\n<dd>Pomaceous <em>fruit</em></dd>\n'
        '<dt>Orange</dt>\n<dd>Citrus fruit</dd>\n</dl>\n'
    )
    assert MarkdownRenderer().render(root) == 'Apple\n: Pomaceous *fruit*\nOrange\n: Citrus fruit\n'


def test_footnote_identifiers_disallow_spaces() -> None:
    markdown = 'a[^foot note]\n\n[^foot note]: bad\n'

    assert render(Parser([Footnote]), markdown) == '<p>a[^foot note]</p>\n<p>[^foot note]: bad</p>\n'


def test_github_disallowed_html_is_not_double_escaped() -> None:
    markdown = '<script>alert(1)</script>\n'
    root = Parser(github).parse(markdown)

    assert root.children[0].data == {'escaped': True}
    assert HTMLRenderer().render(root) == '&lt;script>alert(1)&lt;/script>\n'
