from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import STANDARD_RULES, configured_app
from wenmode import Wenmode

POSITION_RULE_NAMES = {
    *(name for name in STANDARD_RULES if name not in {'atx_heading_id', 'link_no_references'}),
    'abbreviation',
    'block_spoiler',
    'definition_list',
    'fenced_directive',
    'html_container',
    'inline_math',
    'inline_spoiler',
    'insert',
    'mark',
    'math_block',
    'role',
    'ruby',
    'subscript',
    'superscript',
}


class PositionExample(TypedDict, total=False):
    name: str
    rules: list[str]
    markdown: str
    source_lines: list[str]
    ast: dict[str, object]


def source_for_example(example: PositionExample) -> str | Iterable[str]:
    if 'source_lines' in example:
        return iter(example['source_lines'])
    return example['markdown']


def rules_for_example(example: PositionExample) -> Iterable[str] | None:
    if 'rules' in example:
        return example['rules']
    return None


def test_all_position_rules_have_examples() -> None:
    examples = load_fixture('positions.json')
    used_rules = {rule_name for example in examples for rule_name in example.get('rules', [])}
    assert sorted(POSITION_RULE_NAMES - used_rules) == []


@pytest.mark.parametrize(
    'example',
    load_fixture('positions.json'),
    ids=lambda example: example['name'],
)
def test_position_examples(example: PositionExample) -> None:
    app = configured_app(rules_for_example(example), positions=True)
    assert app.parse(source_for_example(example)).to_ast() == example['ast']
