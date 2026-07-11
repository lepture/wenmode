from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import STANDARD_RULES, configured_app
from wenmode import Wenmode

POSITION_RULE_NAMES = {
    *(name for name in STANDARD_RULES if name not in {'atx_heading_id', 'link_no_references'}),
    'abbreviation',
    'block_spoiler',
    'definition_list',
    'fenced_directive',
    'html_container',
    'inline_math',
    'inline_spoiler',
    'insert',
    'mark',
    'math_block',
    'role',
    'ruby',
    'subscript',
    'superscript',
}


class PositionExample(TypedDict, total=False):
    name: str
    rules: list[str]
    markdown: str
    source_lines: list[str]
    ast: dict[str, object]


def source_for_example(example: PositionExample) -> str | Iterable[str]:
    if 'source_lines' in example:
        return iter(example['source_lines'])
    return example['markdown']


def rules_for_example(example: PositionExample) -> Iterable[str] | None:
    if 'rules' in example:
        return example['rules']
    return None


def test_all_position_rules_have_examples() -> None:
    examples = load_fixture('positions.json')
    used_rules = {rule_name for example in examples for rule_name in example.get('rules', [])}
    assert sorted(POSITION_RULE_NAMES - used_rules) == []


@pytest.mark.parametrize(
    'example',
    load_fixture('positions.json'),
    ids=lambda example: example['name'],
)
def test_position_examples(example: PositionExample) -> None:
    app = configured_app(rules_for_example(example), positions=True)
    assert app.parse(source_for_example(example)).to_ast() == example['ast']


@pytest.mark.parametrize('line_ending', ['\n', '\r\n', '\r'], ids=['lf', 'crlf', 'cr'])
def test_heading_positions_follow_string_line_endings(line_ending: str) -> None:
    markdown = f'# a{line_ending}# b{line_ending}'

    ast = Wenmode(positions=True).parse(markdown).to_ast()

    second_offset = len(f'# a{line_ending}')
    assert ast['children'][0]['position']['start'] == {'line': 1, 'column': 1, 'offset': 0}
    assert ast['children'][1]['position']['start'] == {
        'line': 2,
        'column': 1,
        'offset': second_offset,
    }
    assert ast['position']['end'] == {'line': 3, 'column': 1, 'offset': len(markdown)}


def test_position_eof_with_empty_unterminated_and_mixed_sources() -> None:
    app = Wenmode(positions=True)

    assert app.parse('').to_ast()['position']['end'] == {'line': 1, 'column': 1, 'offset': 0}

    unterminated = '# a'
    assert app.parse(unterminated).to_ast()['position']['end'] == {
        'line': 1,
        'column': 4,
        'offset': len(unterminated),
    }

    mixed = '# a\n# b\r\n# c\r'
    ast = app.parse(mixed).to_ast()
    assert [child['position']['start'] for child in ast['children']] == [
        {'line': 1, 'column': 1, 'offset': 0},
        {'line': 2, 'column': 1, 'offset': 4},
        {'line': 3, 'column': 1, 'offset': 9},
    ]
    assert ast['position']['end'] == {'line': 4, 'column': 1, 'offset': len(mixed)}
