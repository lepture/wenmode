from __future__ import annotations

import pytest

from tests.helpers import SpecExample, load_fixture
from wenmode import HTMLRenderer, Wenmode
from wenmode.presets import create_preset, github
from wenmode.rules import ExtendedAutolink, Rule


@pytest.mark.parametrize(
    'example', load_fixture('gfm-0.29.json'), ids=lambda example: f'{example["example"]}: {example["section"]}'
)
def test_gfm_spec(example: SpecExample) -> None:
    renderer = HTMLRenderer(escape=False, sanitize_urls=False)
    parser = Wenmode(rules_for_example(example), renderer)

    assert parser.render(example['markdown']) == example['html']


def rules_for_example(example: SpecExample) -> list[type[Rule] | Rule]:
    if example['section'] == '6.8 Autolinks':
        return create_preset(github, remove=[ExtendedAutolink])
    return github
