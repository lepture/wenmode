from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import HTMLRenderer, Parser
from wenmode.presets import github
from wenmode.rules import ExtendedAutolink, Rule


class GFMExample(TypedDict):
    markdown: str
    html: str
    example: int
    section: str


SPEC_PATH = Path(__file__).parent / 'fixtures' / 'gfm-0.29.json'
GFM_CORE = [rule for rule in github if rule is not ExtendedAutolink and not isinstance(rule, ExtendedAutolink)]


def load_examples() -> list[GFMExample]:
    return json.loads(SPEC_PATH.read_text())


@pytest.mark.parametrize(
    'example',
    load_examples(),
    ids=lambda example: f'{example["example"]}: {example["section"]}',
)
def test_gfm_spec(example: GFMExample) -> None:
    parser = Parser(rules_for_example(example))
    renderer = HTMLRenderer(escape=False, sanitize_urls=False)

    assert renderer.render(parser.parse(example['markdown'])) == example['html']


def rules_for_example(example: GFMExample) -> list[type[Rule] | Rule]:
    if example['section'] == '6.8 Autolinks':
        return GFM_CORE
    return github
