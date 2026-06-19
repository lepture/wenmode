from __future__ import annotations

from collections.abc import Iterable
from typing import Literal, TypedDict

import pytest

from tests.helpers import load_fixture
from wenmode import Wenmode
from wenmode.presets import github
from wenmode.rules import Abbreviation, Blockquote, List, Rule

POSITION_RULES = {
    'abbreviation': Abbreviation,
    'blockquote': Blockquote,
    'list': List,
}
POSITION_PRESETS = {
    'github': github,
}


class PositionExample(TypedDict, total=False):
    name: str
    preset: Literal['github']
    rules: list[str]
    markdown: str
    source_lines: list[str]
    ast: dict[str, object]


def source_for_example(example: PositionExample) -> str | Iterable[str]:
    if 'source_lines' in example:
        return iter(example['source_lines'])
    return example['markdown']


def rules_for_example(example: PositionExample) -> Iterable[type[Rule] | Rule] | None:
    if 'preset' in example:
        return POSITION_PRESETS[example['preset']]
    if 'rules' in example:
        return [POSITION_RULES[name] for name in example['rules']]
    return None


@pytest.mark.parametrize(
    'example',
    load_fixture('positions.json'),
    ids=lambda example: example['name'],
)
def test_position_examples(example: PositionExample) -> None:
    app = Wenmode(rules_for_example(example), positions=True)
    assert app.parse(source_for_example(example)).to_ast() == example['ast']
