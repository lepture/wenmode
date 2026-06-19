from __future__ import annotations

from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import configured_app
from wenmode import MarkdownRenderer, Wenmode
from wenmode.presets import commonmark, github

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


def app_for_example(example: ExtendedRuleExample, renderer: MarkdownRenderer | None = None) -> Wenmode:
    if 'preset' in example:
        return Wenmode(EXTENDED_PRESETS[example['preset']], renderer=renderer)
    return configured_app(example['rules'], renderer=renderer)


@pytest.mark.parametrize(
    'example',
    load_fixture('extended_rules.json'),
    ids=lambda example: example['name'],
)
def test_extended_rule_examples(example: ExtendedRuleExample) -> None:
    assert app_for_example(example).render(example['markdown']) == example['html']

    if 'markdown_output' in example:
        assert (
            app_for_example(example, renderer=MarkdownRenderer()).render(example['markdown'])
            == example['markdown_output']
        )
