from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import Wenmode
from wenmode.rules import (
    Abbreviation,
    AtxHeading,
    BackslashEscape,
    Emphasis,
    ExtendedAutolink,
    FencedCode,
    FencedDirective,
    HardBreak,
    HtmlBlock,
    Image,
    InlineCode,
    Role,
    Ruby,
    SetextHeading,
    Strikethrough,
)
from wenmode.rules import BlockSpoiler as BlockSpoilerRule
from wenmode.rules import ContainerDirective as ContainerDirectiveRule
from wenmode.rules import DefinitionList as DefinitionListRule
from wenmode.rules import Footnote as FootnoteRule
from wenmode.rules import InlineMath as InlineMathRule
from wenmode.rules import InlineSpoiler as InlineSpoilerRule
from wenmode.rules import LeafDirective as LeafDirectiveBlockRule
from wenmode.rules import Link as LinkRule
from wenmode.rules import List as ListRule
from wenmode.rules import MathBlock as MathBlockRule
from wenmode.rules import Table as TableRule
from wenmode.rules import TextDirective as TextDirectiveInlineRule

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
RULE_EDGE_RULES = {
    'abbreviation': Abbreviation,
    'atx_heading': AtxHeading,
    'backslash_escape': BackslashEscape,
    'block_spoiler': BlockSpoilerRule,
    'container_directive': ContainerDirectiveRule,
    'definition_list': DefinitionListRule,
    'emphasis': Emphasis,
    'extended_autolink': ExtendedAutolink,
    'fenced_code': FencedCode,
    'fenced_directive': FencedDirective,
    'footnote': FootnoteRule,
    'hard_break': HardBreak,
    'html_block': HtmlBlock,
    'image': Image,
    'inline_code': InlineCode,
    'inline_math': InlineMathRule,
    'inline_spoiler': InlineSpoilerRule,
    'leaf_directive': LeafDirectiveBlockRule,
    'link': LinkRule,
    'link_no_references': LinkRule(references=False),
    'list': ListRule,
    'math_block': MathBlockRule,
    'role': Role,
    'ruby': Ruby,
    'setext_heading': SetextHeading,
    'strikethrough': Strikethrough,
    'table': TableRule,
    'task_list': ListRule(task=True),
    'text_directive': TextDirectiveInlineRule,
}


class RuleEdgeExample(TypedDict, total=False):
    name: str
    rules: list[str]
    markdown: str
    html: str
    max_container_depth: int


def load_rule_edge_examples() -> list[RuleEdgeExample]:
    return json.loads((FIXTURES_DIR / 'rule_edges.json').read_text())


def app_for_rule_edge(example: RuleEdgeExample) -> Wenmode:
    app = Wenmode([RULE_EDGE_RULES[name] for name in example['rules']])
    if 'max_container_depth' in example:
        app.parser.max_container_depth = example['max_container_depth']
    return app


@pytest.mark.parametrize(
    'example',
    load_rule_edge_examples(),
    ids=lambda example: example['name'],
)
def test_rule_edge_examples(example: RuleEdgeExample) -> None:
    assert app_for_rule_edge(example).render(example['markdown']) == example['html']
