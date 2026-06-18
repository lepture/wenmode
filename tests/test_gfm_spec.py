from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

import pytest

from wenmode import HTMLRenderer, Parser
from wenmode.presets import github


class GFMExample(TypedDict):
    markdown: str
    html: str
    example: int
    section: str


SPEC_PATH = Path(__file__).parent / 'fixtures' / 'gfm-0.29.json'
SKIPPED_EXAMPLES = {
    620: 'extended autolinks are enabled in the GITHUB preset',
    621: 'extended autolinks are enabled in the GITHUB preset',
}


def load_examples() -> list[GFMExample]:
    return json.loads(SPEC_PATH.read_text())


def example_parameters() -> list[Any]:
    parameters = []
    for example in load_examples():
        reason = SKIPPED_EXAMPLES.get(example['example'])
        if reason is None:
            parameters.append(example)
        else:
            parameters.append(pytest.param(example, marks=pytest.mark.skip(reason=reason)))
    return parameters


@pytest.mark.parametrize(
    'example',
    example_parameters(),
    ids=lambda example: f'{example["example"]}: {example["section"]}',
)
def test_gfm_spec(example: GFMExample) -> None:
    parser = Parser(github)
    renderer = HTMLRenderer(escape=False, sanitize_urls=False)

    assert renderer.render(parser.parse(example['markdown'])) == example['html']
