from __future__ import annotations

import pytest

from tests.helpers import SpecExample, load_fixture
from wenmode import HTMLRenderer, Wenmode
from wenmode.presets import commonmark


@pytest.mark.parametrize(
    'example', load_fixture('commonmark-0.31.2.json'), ids=lambda example: f'{example["example"]}: {example["section"]}'
)
def test_commonmark_spec(example: SpecExample) -> None:
    renderer = HTMLRenderer(escape=False, sanitize_urls=False)
    parser = Wenmode(commonmark, renderer)

    assert parser.render(example['markdown']) == example['html']
