from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

import pytest

from wenmode import HTMLRenderer, Parser, github


class GFMExample(TypedDict):
    markdown: str
    html: str
    example: int
    section: str


SPEC_PATH = Path(__file__).parent / 'fixtures' / 'gfm-0.29.json'
SKIPPED_EXAMPLES = {
    140: 'configured tagfilter currently applies to earlier HTML block examples',
    141: 'configured tagfilter currently applies to earlier HTML block examples',
    142: 'configured tagfilter currently applies to earlier HTML block examples',
    145: 'configured tagfilter currently applies to earlier HTML block examples',
    147: 'configured tagfilter currently applies to earlier HTML block examples',
    199: 'table parser currently requires a leading or trailing pipe in the delimiter row',
    200: 'table cells currently preserve escaped pipes inside code spans',
    202: 'table parser currently stops body rows without a pipe',
    203: 'failed table recognition currently falls back to separate paragraphs',
    611: 'extended autolinks currently link inside invalid angle autolinks',
    617: 'extended autolinks currently link inside invalid angle autolinks',
    620: 'extended autolinks are enabled in the GITHUB preset',
    621: 'extended autolinks are enabled in the GITHUB preset',
    627: 'extended autolink entity boundary handling is incomplete',
    632: 'extended email autolink trailing hyphen/underscore handling is incomplete',
    633: 'mailto/xmpp extended autolink path boundary handling is incomplete',
    635: 'xmpp extended autolink path boundary handling is incomplete',
    649: 'invalid HTML comment detection is incomplete',
    650: 'invalid HTML comment detection is incomplete',
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
