from __future__ import annotations

import re

from wenmode import Parser, Wenmode
from wenmode.nodes import Node, Parent, Text
from wenmode.rules import AtxHeading, BlockRule, InlineCode, InlineRule
from wenmode.state import BlockState, SourceMap, SourceSegment


class BoxNode(Parent):
    def __init__(self, children: list[Node]) -> None:
        super().__init__('box', children=children)


def test_source_map_preserves_boundary_and_line_offset_semantics() -> None:
    source = SourceMap(
        'abcdef',
        [
            SourceSegment(0, 2, 10),
            SourceSegment(2, 4, 30),
            SourceSegment(4, 6, 80),
        ],
    )

    assert [source.source_offset(offset) for offset in (-1, 0, 1, 2, 6, 99)] == [10, 10, 11, 30, 82, 82]
    assert source.line_offsets(['ab', 'cd', 'ef']) == [10, 30, 80]


def test_source_map_preserves_duplicate_and_zero_length_segment_semantics() -> None:
    source = SourceMap(
        'ab',
        [
            SourceSegment(0, 0, 5),
            SourceSegment(0, 1, 10),
            SourceSegment(1, 1, 20),
            SourceSegment(1, 2, 30),
        ],
    )

    assert source.source_offset(0) == 5
    assert source.source_offset(1) == 20
    assert source.source_offset(2) == 31


def test_source_map_preserves_first_match_order_for_arbitrary_segments() -> None:
    source = SourceMap(
        'abcdefgh',
        [
            SourceSegment(0, 8, 100),
            SourceSegment(4, 6, 20),
            SourceSegment(2, 7, 60),
        ],
    )

    assert source.source_offset(3) == 103
    assert source.source_offset(4) == 20
    assert source.source_offset(5) == 105

    decreasing_ends = SourceMap(
        'abcdefgh',
        [SourceSegment(0, 8, 100), SourceSegment(4, 6, 20)],
    )
    assert decreasing_ends.source_offset(4) == 20
    assert decreasing_ends.source_offset(5) == 105

    overlapping_slice = decreasing_ends.slice(5, 6)
    assert overlapping_slice.segments == [
        SourceSegment(0, 1, 105),
        SourceSegment(0, 1, 105),
    ]


def test_source_map_preserves_partial_empty_and_missing_segment_slices() -> None:
    source = SourceMap(
        'abcdef',
        [
            SourceSegment(0, 2, 10),
            SourceSegment(2, 4, 30),
            SourceSegment(4, 6, 80),
        ],
    )

    partial = source.slice(1, 5)
    assert partial.text == 'bcde'
    assert partial.segments == [
        SourceSegment(0, 1, 11),
        SourceSegment(1, 3, 30),
        SourceSegment(3, 4, 80),
    ]
    empty = source.slice(3, 3)
    assert empty.text == ''
    assert empty.source_offset(0) == 31
    shared_boundary = source.slice(2, 2)
    assert shared_boundary.segments == [
        SourceSegment(0, 0, 30),
        SourceSegment(0, 0, 30),
    ]

    empty_map = SourceMap('abc', [])
    assert empty_map.source_offset(99) == 0
    missing = empty_map.slice(1, 2)
    assert missing.text == 'b'
    assert missing.segments == [SourceSegment(0, 0, 0)]


def test_nested_block_and_inline_source_maps_share_parent_state() -> None:
    class BoxRule(BlockRule):
        name = 'box'
        pattern = r'[ \t]{0,3}::box[ \t]*$'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            state.advance()
            lines: list[str] = []
            source = state.source.collect()
            while not state.done:
                if re.match(r'[ \t]{0,3}::[ \t]*$', state.line):
                    state.advance()
                    break
                source.add(state.index, 0, state.line)
                lines.append(state.line)
                state.advance()
            return BoxNode(parser.parse_blocks(''.join(lines), state, source=source.map()))

    app = Wenmode([BoxRule, AtxHeading, InlineCode], positions=True)
    root = app.parse('lead\n\n::box\n# Title\n\nText `code`.\n::\n')

    box = root.to_ast()['children'][1]

    assert box['type'] == 'box'
    assert box['position'] == {
        'start': {'line': 3, 'column': 1, 'offset': 6},
        'end': {'line': 8, 'column': 1, 'offset': 37},
    }
    assert box['children'][0]['position'] == {
        'start': {'line': 4, 'column': 1, 'offset': 12},
        'end': {'line': 5, 'column': 1, 'offset': 20},
    }
    assert box['children'][0]['children'][0]['position'] == {
        'start': {'line': 4, 'column': 3, 'offset': 14},
        'end': {'line': 4, 'column': 8, 'offset': 19},
    }
    assert box['children'][1]['children'][1] == {
        'type': 'inlineCode',
        'position': {
            'start': {'line': 6, 'column': 6, 'offset': 26},
            'end': {'line': 6, 'column': 12, 'offset': 32},
        },
        'value': 'code',
    }


def test_inline_sources_are_state_local() -> None:
    other_state = BlockState([])
    observations: list[tuple[int, int, bool]] = []

    class ProbeSource(InlineRule):
        name = 'probe_source'
        pattern = r'!'
        trigger_chars = '!'

        def parse(
            self, parser: Parser, text: str, match: re.Match[str], state: BlockState
        ) -> tuple[Node | None, int]:
            current_source = parser.inline_source(text, state, match.start(), match.end())
            other_source = parser.inline_source(text, other_state, match.start(), match.end())
            assert current_source is not None
            observations.append(
                (
                    current_source.source_offset(0),
                    current_source.source_offset(1),
                    other_source is None,
                )
            )
            return Text(value='!'), match.end()

    parser = Parser([ProbeSource], positions=True)
    state = BlockState([])

    parser.parse_inlines('!', state, source=SourceMap.contiguous('!', 42))

    assert observations == [(42, 43, True)]
    assert state.inline_sources == []
    assert other_state.inline_sources == []
