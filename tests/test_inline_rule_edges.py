from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import Wenmode
from wenmode.rules import ExtendedAutolink as ExtendedAutolinkRule
from wenmode.rules import Image as ImageRule
from wenmode.rules import InlineMath as InlineMathRule
from wenmode.rules import InlineSpoiler as InlineSpoilerRule
from wenmode.rules import Link as LinkRule
from wenmode.rules import Ruby as RubyRule
from wenmode.rules import Strikethrough

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class InlineRuleEdgeExample(TypedDict):
    name: str
    rules: list[str]
    markdown: str
    html: str


def load_inline_rule_edge_examples() -> list[InlineRuleEdgeExample]:
    return json.loads((FIXTURES_DIR / 'inline_rule_edges.json').read_text())


def inline_edge_rule(name: str):
    if name == 'link_no_references':
        return LinkRule(references=False)
    return {
        'extended_autolink': ExtendedAutolinkRule,
        'image': ImageRule,
        'inline_math': InlineMathRule,
        'inline_spoiler': InlineSpoilerRule,
        'link': LinkRule,
        'ruby': RubyRule,
        'strikethrough': Strikethrough,
    }[name]


@pytest.mark.parametrize(
    'example',
    load_inline_rule_edge_examples(),
    ids=lambda example: example['name'],
)
def test_inline_rule_edge_examples(example: InlineRuleEdgeExample) -> None:
    app = Wenmode([inline_edge_rule(name) for name in example['rules']])

    assert app.render(example['markdown']) == example['html']
