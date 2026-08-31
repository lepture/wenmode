from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import STANDARD_RULES, configured_app
from wenmode import Wenmode
from wenmode.presets import github, streaming
from wenmode.rules import ContainerDirective

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
    rules: Iterable[str]
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


@pytest.mark.parametrize('example', load_fixture('positions.json'), ids=lambda example: example['name'])
def test_position_examples(example: PositionExample) -> None:
    app = configured_app(rules_for_example(example), positions=True)
    assert app.parse(source_for_example(example)).to_ast() == example['ast']


@pytest.mark.parametrize('line_ending', ['\n', '\r\n', '\r'], ids=['lf', 'crlf', 'cr'])
def test_heading_positions_follow_string_line_endings(line_ending: str) -> None:
    markdown = f'# a{line_ending}# b{line_ending}'

    ast = Wenmode(positions=True).parse(markdown).to_ast()

    second_offset = len(f'# a{line_ending}')
    assert ast['children'][0]['position']['start'] == {'line': 1, 'column': 1, 'offset': 0}
    assert ast['children'][1]['position']['start'] == {'line': 2, 'column': 1, 'offset': second_offset}
    assert ast['position']['end'] == {'line': 3, 'column': 1, 'offset': len(markdown)}


def test_iterable_source_positions_support_carriage_return_lines() -> None:
    ast = Wenmode(positions=True).parse(iter(['# a\r', '# b\r'])).to_ast()

    assert [child['position']['start'] for child in ast['children']] == [
        {'line': 1, 'column': 1, 'offset': 0},
        {'line': 2, 'column': 1, 'offset': 4},
    ]
    assert ast['position']['end'] == {'line': 3, 'column': 1, 'offset': 8}


def test_iterable_setext_heading_maps_trimmed_inline_positions() -> None:
    markdown = '  **Title**  \n---\n'
    app = Wenmode(positions=True)

    ast = app.parse(iter(markdown.splitlines(keepends=True))).to_ast()

    assert ast == app.parse(markdown).to_ast()
    heading = ast['children'][0]
    assert heading['position'] == {
        'start': {'line': 1, 'column': 1, 'offset': 0},
        'end': {'line': 3, 'column': 1, 'offset': len(markdown)},
    }
    assert heading['children'][0]['position'] == {
        'start': {'line': 1, 'column': 3, 'offset': 2},
        'end': {'line': 1, 'column': 12, 'offset': 11},
    }
    assert heading['children'][0]['children'][0]['position'] == {
        'start': {'line': 1, 'column': 5, 'offset': 4},
        'end': {'line': 1, 'column': 10, 'offset': 9},
    }


@pytest.mark.parametrize(
    ('markdown', 'emphasis_positions', 'emphasis_values'),
    [
        ('> *a*\n> *b*\n> *c*\n', [(2, 5), (8, 11), (14, 17)], ['*a*', '*b*', '*c*']),
        ('>> *a*\n>> *b*\n', [(3, 6), (10, 13)], ['*a*', '*b*']),
        ('>*a*\n>*b*\n', [(1, 4), (6, 9)], ['*a*', '*b*']),
    ],
    ids=['multiline', 'nested', 'no-space'],
)
def test_blockquote_inline_positions_account_for_each_line_prefix(
    markdown: str, emphasis_positions: list[tuple[int, int]], emphasis_values: list[str]
) -> None:
    root = Wenmode(positions=True).parse(markdown)
    paragraph = root.children[0]
    while paragraph.type == 'blockquote':
        paragraph = paragraph.children[0]

    positions = [
        (child.position.start, child.position.end)
        for child in paragraph.children
        if child.type == 'emphasis' and child.position is not None
    ]

    assert positions == emphasis_positions
    assert [markdown[start:end] for start, end in positions] == emphasis_values


def test_emphasis_position_spans_noncontiguous_blockquote_source_segments() -> None:
    markdown = '> *a\n> b*\n'
    emphasis = Wenmode(positions=True).parse(markdown).children[0].children[0].children[0]

    assert emphasis.position is not None
    assert (emphasis.position.start, emphasis.position.end) == (2, 9)
    assert emphasis.children[0].position is not None
    assert (emphasis.children[0].position.start, emphasis.children[0].position.end) == (3, 8)


@pytest.mark.parametrize('line_ending', ['\n', '\r\n', '\r'], ids=['lf', 'crlf', 'cr'])
def test_iterable_source_positions_match_string_line_endings(line_ending: str) -> None:
    markdown = (
        f'# a{line_ending}'
        f'{line_ending}'
        f'| a | b |{line_ending}'
        f'| --- | --- |{line_ending}'
        f'| c | d |{line_ending}'
        f'{line_ending}'
        f'- one{line_ending}'
        f'- two{line_ending}'
    )
    app = Wenmode(github(), positions=True)

    assert app.parse(iter(markdown.splitlines(keepends=True))).to_ast() == app.parse(markdown).to_ast()


def test_parse_iter_positions_stay_absolute_after_table_and_list_lookahead() -> None:
    markdown = '| a | b |\n| --- | --- |\n| c | d |\n\n- one\n- two\n'
    nodes = list(Wenmode(streaming(), positions=True).parser.parse_iter(iter(markdown.splitlines(keepends=True))))

    assert [node.type for node in nodes] == ['table', 'list']
    assert nodes[0].to_ast()['position'] == {'start': {'offset': 0}, 'end': {'offset': 34}}
    assert nodes[1].to_ast()['position'] == {'start': {'offset': 35}, 'end': {'offset': len(markdown)}}
    assert nodes[0].to_ast()['children'][0]['children'][0]['children'][0]['position'] == {
        'start': {'offset': 2},
        'end': {'offset': 3},
    }
    assert nodes[1].to_ast()['children'][1]['children'][0]['children'][0]['position'] == {
        'start': {'offset': 43},
        'end': {'offset': 46},
    }


def test_shallow_nested_block_positions_stay_absolute_at_depth_limit() -> None:
    markdown = ':::note\n  *deep*\n\n  tail\n:::\n'
    app = Wenmode([ContainerDirective], positions=True)
    app.parser.max_container_depth = 1

    assert app.parse(markdown).to_ast() == {
        'type': 'root',
        'children': [
            {
                'type': 'containerDirective',
                'children': [
                    {
                        'type': 'paragraph',
                        'children': [
                            {
                                'type': 'text',
                                'value': '*deep*',
                                'position': {
                                    'start': {'line': 2, 'column': 3, 'offset': 10},
                                    'end': {'line': 2, 'column': 9, 'offset': 16},
                                },
                            }
                        ],
                        'position': {
                            'start': {'line': 2, 'column': 1, 'offset': 8},
                            'end': {'line': 3, 'column': 1, 'offset': 17},
                        },
                    },
                    {
                        'type': 'paragraph',
                        'children': [
                            {
                                'type': 'text',
                                'value': 'tail',
                                'position': {
                                    'start': {'line': 4, 'column': 3, 'offset': 20},
                                    'end': {'line': 4, 'column': 7, 'offset': 24},
                                },
                            }
                        ],
                        'position': {
                            'start': {'line': 4, 'column': 1, 'offset': 18},
                            'end': {'line': 5, 'column': 1, 'offset': 25},
                        },
                    },
                ],
                'name': 'note',
                'position': {
                    'start': {'line': 1, 'column': 1, 'offset': 0},
                    'end': {'line': 6, 'column': 1, 'offset': 29},
                },
            }
        ],
        'position': {'start': {'line': 1, 'column': 1, 'offset': 0}, 'end': {'line': 6, 'column': 1, 'offset': 29}},
    }


def test_position_eof_with_empty_unterminated_and_mixed_sources() -> None:
    app = Wenmode(positions=True)

    assert app.parse('').to_ast()['position']['end'] == {'line': 1, 'column': 1, 'offset': 0}

    unterminated = '# a'
    assert app.parse(unterminated).to_ast()['position']['end'] == {'line': 1, 'column': 4, 'offset': len(unterminated)}

    mixed = '# a\n# b\r\n# c\r'
    ast = app.parse(mixed).to_ast()
    assert [child['position']['start'] for child in ast['children']] == [
        {'line': 1, 'column': 1, 'offset': 0},
        {'line': 2, 'column': 1, 'offset': 4},
        {'line': 3, 'column': 1, 'offset': 9},
    ]
    assert ast['position']['end'] == {'line': 4, 'column': 1, 'offset': len(mixed)}
