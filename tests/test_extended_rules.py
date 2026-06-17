from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import HTMLRenderer, Parser
from wenmode.presets import commonmark, github
from wenmode.rules import Blockquote, Emphasis, Footnote, InlineCode, InlineMath, Link, MathBlock

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


def test_footnote_identifiers_disallow_spaces() -> None:
    markdown = 'a[^foot note]\n\n[^foot note]: bad\n'

    assert render(Parser([Footnote]), markdown) == '<p>a[^foot note]</p>\n<p>[^foot note]: bad</p>\n'


def test_github_disallowed_html_is_not_double_escaped() -> None:
    markdown = '<script>alert(1)</script>\n'
    root = Parser(github).parse(markdown)

    assert root.children[0].data == {'escaped': True}
    assert HTMLRenderer().render(root) == '&lt;script>alert(1)&lt;/script>\n'
