from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import HTMLRenderer, Wenmode
from wenmode.rules import Blockquote, Emphasis, Footnote, Link

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class ExtendedRuleExample(TypedDict):
    name: str
    markdown: str
    html: str


def load_examples(name: str) -> list[ExtendedRuleExample]:
    return json.loads((FIXTURES_DIR / name).read_text())


def render(parser: Wenmode, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


@pytest.mark.parametrize(
    'example',
    load_examples('footnotes.json'),
    ids=lambda example: example['name'],
)
def test_footnote_examples(example: ExtendedRuleExample) -> None:
    parser = Wenmode([Footnote, Emphasis, Blockquote, Link])

    assert render(parser, example['markdown']) == example['html']
