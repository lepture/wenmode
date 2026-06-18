from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import MarkdownRenderer, Wenmode
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
EXTENDED_RULES = {
    'abbreviation': Abbreviation,
    'backslash_escape': BackslashEscape,
    'blockquote': Blockquote,
    'block_spoiler': BlockSpoiler,
    'definition_list': DefinitionList,
    'emphasis': Emphasis,
    'footnote': Footnote,
    'inline_code': InlineCode,
    'inline_math': InlineMath,
    'inline_spoiler': InlineSpoiler,
    'insert': Insert,
    'link': Link,
    'mark': Mark,
    'math_block': MathBlock,
    'ruby': Ruby,
    'strikethrough': Strikethrough,
    'subscript': Subscript,
    'superscript': Superscript,
}
EXTENDED_PRESETS = {
    'commonmark': commonmark,
    'github': github,
}


class ExtendedRuleExample(TypedDict, total=False):
    name: str
    preset: str
    rules: list[str]
    markdown: str
    html: str
    markdown_output: str


def load_examples(name: str) -> list[ExtendedRuleExample]:
    return json.loads((FIXTURES_DIR / name).read_text())


def app_for_example(example: ExtendedRuleExample, renderer: MarkdownRenderer | None = None) -> Wenmode:
    rules = (
        EXTENDED_PRESETS[example['preset']]
        if 'preset' in example
        else [EXTENDED_RULES[name] for name in example['rules']]
    )
    return Wenmode(rules, renderer=renderer)


@pytest.mark.parametrize(
    'example',
    load_examples('extended_rules.json'),
    ids=lambda example: example['name'],
)
def test_extended_rule_examples(example: ExtendedRuleExample) -> None:
    assert app_for_example(example).render(example['markdown']) == example['html']

    if 'markdown_output' in example:
        assert (
            app_for_example(example, renderer=MarkdownRenderer()).render(example['markdown'])
            == example['markdown_output']
        )
