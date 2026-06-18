from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import Wenmode
from wenmode.rules import Footnote as FootnoteRule
from wenmode.rules import Link, Role
from wenmode.rules import TextDirective as TextDirectiveInlineRule

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
DIRECTIVE_REFERENCE_EDGE_RULES = {
    'footnote': FootnoteRule,
    'link': Link,
    'role': Role,
    'text_directive': TextDirectiveInlineRule,
}


class DirectiveReferenceEdgeExample(TypedDict):
    name: str
    rules: list[str]
    markdown: str
    html: str


def load_directive_reference_edge_examples() -> list[DirectiveReferenceEdgeExample]:
    return json.loads((FIXTURES_DIR / 'directive_reference_edges.json').read_text())


@pytest.mark.parametrize(
    'example',
    load_directive_reference_edge_examples(),
    ids=lambda example: example['name'],
)
def test_directive_reference_edge_examples(example: DirectiveReferenceEdgeExample) -> None:
    app = Wenmode([DIRECTIVE_REFERENCE_EDGE_RULES[name] for name in example['rules']])

    assert app.render(example['markdown']) == example['html']
