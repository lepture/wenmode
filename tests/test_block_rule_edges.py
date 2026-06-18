from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import Wenmode
from wenmode.rules import Abbreviation, AtxHeading, FencedCode, FencedDirective, HtmlBlock, SetextHeading
from wenmode.rules import BlockSpoiler as BlockSpoilerRule
from wenmode.rules import ContainerDirective as ContainerDirectiveRule
from wenmode.rules import DefinitionList as DefinitionListRule
from wenmode.rules import LeafDirective as LeafDirectiveBlockRule
from wenmode.rules import List as ListRule
from wenmode.rules import MathBlock as MathBlockRule
from wenmode.rules import Table as TableRule

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
BLOCK_EDGE_RULES = {
    'abbreviation': Abbreviation,
    'atx_heading': AtxHeading,
    'block_spoiler': BlockSpoilerRule,
    'container_directive': ContainerDirectiveRule,
    'definition_list': DefinitionListRule,
    'fenced_code': FencedCode,
    'fenced_directive': FencedDirective,
    'html_block': HtmlBlock,
    'leaf_directive': LeafDirectiveBlockRule,
    'list': ListRule,
    'math_block': MathBlockRule,
    'setext_heading': SetextHeading,
    'table': TableRule,
    'task_list': ListRule(task=True),
}


class BlockRuleEdgeExample(TypedDict, total=False):
    name: str
    rules: list[str]
    markdown: str
    html: str
    max_container_depth: int


def load_block_rule_edge_examples() -> list[BlockRuleEdgeExample]:
    return json.loads((FIXTURES_DIR / 'block_rule_edges.json').read_text())


def app_for_block_rule_edge(example: BlockRuleEdgeExample) -> Wenmode:
    app = Wenmode([BLOCK_EDGE_RULES[name] for name in example['rules']])
    if 'max_container_depth' in example:
        app.parser.max_container_depth = example['max_container_depth']
    return app


@pytest.mark.parametrize(
    'example',
    load_block_rule_edge_examples(),
    ids=lambda example: example['name'],
)
def test_block_rule_edge_examples(example: BlockRuleEdgeExample) -> None:
    assert app_for_block_rule_edge(example).render(example['markdown']) == example['html']
