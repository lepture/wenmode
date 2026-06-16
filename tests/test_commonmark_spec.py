from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import COMMON_MARK, HTMLRenderer, Wenmode


class CommonMarkExample(TypedDict):
    markdown: str
    html: str
    example: int
    section: str


SPEC_PATH = Path(__file__).parent / 'fixtures' / 'commonmark-0.31.2.json'


def load_examples() -> list[CommonMarkExample]:
    return json.loads(SPEC_PATH.read_text())


@pytest.mark.parametrize(
    'example',
    load_examples(),
    ids=lambda example: f'{example["example"]}: {example["section"]}',
)
def test_commonmark_spec(example: CommonMarkExample) -> None:
    parser = Wenmode(COMMON_MARK)
    renderer = HTMLRenderer()

    assert renderer.render(parser.parse(example['markdown'])) == example['html']
