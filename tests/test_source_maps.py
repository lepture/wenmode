from __future__ import annotations

import re

from wenmode import Parser, Wenmode
from wenmode.nodes import Node, Paragraph, Parent, Text
from wenmode.rules import AtxHeading, BlockRule, InlineCode, InlineRule, SetextHeading
from wenmode.state import BlockState, SourceMap, SourceSegment


class BoxNode(Parent):
    def __init__(self, children: list[Node]) -> None:
        super().__init__('box', children=children)


class SyntheticInlineSourceRule(BlockRule):
    name = 'synthetic_inline_source'
    pattern = r'::source[ \t]*$'

    def __init__(self, text: str, source: SourceMap) -> None:
        super().__init__()
        self.text = text
        self.source = source

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        state.advance()
        return BoxNode([Paragraph(children=parser.parse_inlines(self.text, state, source=self.source))])


class SyntheticBlockSourceRule(SyntheticInlineSourceRule):
    name = 'synthetic_block_source'

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        state.advance()
        return BoxNode(parser.parse_blocks(self.text, state, source=self.source))


class ProbeLetter(InlineRule):
    name = 'probe_letter'
    pattern = r'[A-Za-z]'
    trigger_chars = 'abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ'

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        match = self.compiled.match(text, start)
        if match is None:
            return None, start
        return Node(type=f'probe_{match.group(0)}'), match.end()


def probe_positions(text: str, source: SourceMap) -> list[tuple[str, int | None, int | None]]:
    root = Wenmode([SyntheticInlineSourceRule(text, source), ProbeLetter], positions=True).parse('::source\n')
    paragraph = root.children[0].children[0]
    return [
        (child.type, child.position.start if child.position is not None else None, child.position.end if child.position else None)
        for child in paragraph.children
        if child.type.startswith('probe_')
    ]


def nested_probe_positions(text: str, source: SourceMap) -> list[tuple[str, int | None, int | None]]:
    root = Wenmode([SyntheticBlockSourceRule(text, source), ProbeLetter], positions=True).parse('::source\n')
    paragraph = root.children[0].children[0]
    return [
        (child.type, child.position.start if child.position is not None else None, child.position.end if child.position else None)
        for child in paragraph.children
        if child.type.startswith('probe_')
    ]


def nested_setext_probe_positions(text: str, source: SourceMap) -> list[tuple[str, int | None, int | None]]:
    root = Wenmode([SyntheticBlockSourceRule(text, source), SetextHeading, ProbeLetter], positions=True).parse(
        '::source\n'
    )
    heading = root.children[0].children[0]
    return [
        (child.type, child.position.start if child.position is not None else None, child.position.end if child.position else None)
        for child in heading.children
        if child.type.startswith('probe_')
    ]


def test_wenmode_maps_nested_blocks_across_source_segments() -> None:
    source = SourceMap(
        'a\nbc\nde\nf',
        [
            SourceSegment(0, 2, 10),
            SourceSegment(2, 5, 30),
            SourceSegment(5, 8, 80),
            SourceSegment(8, 9, 100),
        ],
    )

    assert probe_positions('a\nbc\nde\nf', source) == [
        ('probe_a', 10, 11),
        ('probe_b', 30, 31),
        ('probe_c', 31, 32),
        ('probe_d', 80, 81),
        ('probe_e', 81, 82),
        ('probe_f', 100, 101),
    ]


def test_wenmode_nested_block_line_offsets_use_source_map() -> None:
    source = SourceMap(
        'a\nbc\nde\nf',
        [
            SourceSegment(0, 2, 10),
            SourceSegment(2, 5, 30),
            SourceSegment(5, 8, 80),
            SourceSegment(8, 9, 100),
        ],
    )

    assert nested_probe_positions('a\nbc\nde\nf', source) == [
        ('probe_a', 10, 11),
        ('probe_b', 30, 31),
        ('probe_c', 31, 32),
        ('probe_d', 80, 81),
        ('probe_e', 81, 82),
        ('probe_f', 100, 101),
    ]


def test_wenmode_preserves_duplicate_and_zero_length_source_boundaries() -> None:
    source = SourceMap(
        'ab',
        [SourceSegment(0, 0, 5), SourceSegment(0, 1, 10), SourceSegment(1, 1, 20), SourceSegment(1, 2, 30)],
    )

    assert probe_positions('ab', source) == [('probe_a', 5, 20), ('probe_b', 20, 31)]


def test_wenmode_empty_source_map_falls_back_to_zero_width_positions() -> None:
    source = SourceMap('ab', [])

    assert probe_positions('ab', source) == [('probe_a', 0, 0), ('probe_b', 0, 0)]


def test_wenmode_preserves_first_match_order_for_overlapping_source_segments() -> None:
    source = SourceMap('abcdefgh', [SourceSegment(0, 8, 100), SourceSegment(4, 6, 20), SourceSegment(2, 7, 60)])

    positions = probe_positions('abcdefgh', source)

    assert positions[3:6] == [('probe_d', 103, 20), ('probe_e', 20, 105), ('probe_f', 105, 106)]


def test_wenmode_maps_single_segment_source_slices() -> None:
    source = SourceMap.from_parts([('  abc  ', 40)])

    assert probe_positions('abc', source.slice(2, 5)) == [('probe_a', 42, 43), ('probe_b', 43, 44), ('probe_c', 44, 45)]


def test_wenmode_source_map_clamped_full_slice_keeps_inline_positions() -> None:
    source = SourceMap.contiguous('  abc  ', 40)

    assert probe_positions('abc', source.slice(-10, 99).slice(2, 5)) == [
        ('probe_a', 42, 43),
        ('probe_b', 43, 44),
        ('probe_c', 44, 45),
    ]


def test_wenmode_source_map_empty_slice_collapses_inline_positions() -> None:
    source = SourceMap.contiguous('abc', 40).slice(5, 2)

    assert probe_positions('a', source) == [('probe_a', 43, 43)]


def test_wenmode_source_map_gap_slice_uses_nearest_source_boundary() -> None:
    source = SourceMap('abcdef', [SourceSegment(5, 6, 50)]).slice(0, 1)

    assert probe_positions('a', source) == [('probe_a', 50, 50)]


def test_wenmode_keeps_irregular_line_offset_fallback_semantics() -> None:
    source = SourceMap('a\nb\nc', [SourceSegment(0, 5, 10), SourceSegment(2, 3, 50)])

    assert nested_probe_positions('a\nb\nc', source) == [('probe_a', 10, 11), ('probe_b', 50, 51), ('probe_c', 14, 15)]


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
        'position': {'start': {'line': 6, 'column': 6, 'offset': 26}, 'end': {'line': 6, 'column': 12, 'offset': 32}},
        'value': 'code',
    }


def test_inline_sources_are_state_local() -> None:
    other_state = BlockState([])
    observations: list[tuple[int, int, bool]] = []

    class ProbeSource(InlineRule):
        name = 'probe_source'
        pattern = r'!'
        trigger_chars = '!'

        def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
            match = self.compiled.match(text, start)
            if match is None:
                return None, start
            current_source = parser.inline_source(text, state, start, match.end())
            other_source = parser.inline_source(text, other_state, start, match.end())
            assert current_source is not None
            observations.append(
                (current_source.source_offset(0), current_source.source_offset(1), other_source is None)
            )
            return Text(value='!'), match.end()

    Wenmode([ProbeSource], positions=True).parse('!')

    assert other_state.inline_sources == []
    assert observations == [(0, 1, True)]


def test_wenmode_collected_nested_paragraph_positions_trim_source() -> None:
    class TrimBoxRule(BlockRule):
        name = 'trim_box'
        pattern = r'::trim[ \t]*$'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            state.advance()
            lines: list[str] = []
            source = state.source.collect()
            while not state.done:
                if re.match(r'::[ \t]*$', state.line):
                    state.advance()
                    break
                source.add(state.index, 0, state.line)
                lines.append(state.line)
                state.advance()
            return BoxNode(parser.parse_blocks(''.join(lines), state, source=source.map()))

    root = Wenmode([TrimBoxRule], positions=True).parse('::trim\n  first\n  second  \n::\n').to_ast()

    assert root['children'][0]['children'][0]['children'][0] == {
        'type': 'text',
        'position': {'start': {'line': 2, 'column': 3, 'offset': 9}, 'end': {'line': 3, 'column': 9, 'offset': 23}},
        'value': 'first\nsecond',
    }


def test_wenmode_collected_noncontiguous_nested_paragraph_positions_trim_source() -> None:
    class SplitParagraphRule(BlockRule):
        name = 'split_paragraph'
        pattern = r'::split[ \t]*$'

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            state.advance()
            source = state.source.collect()

            first = state.line
            source.add(state.index, 0, first)
            state.advance()

            second = state.line[2:]
            source.add(state.index, 2, second)
            state.advance()

            return BoxNode(parser.parse_blocks(first + second, state, source=source.map()))

    root = Wenmode([SplitParagraphRule], positions=True).parse('::split\n  alpha\nxx  beta  \n').to_ast()

    assert root['children'][0]['children'][0]['children'][0] == {
        'type': 'text',
        'position': {'start': {'line': 2, 'column': 3, 'offset': 10}, 'end': {'line': 3, 'column': 9, 'offset': 24}},
        'value': 'alpha\nbeta',
    }


def test_wenmode_noncontiguous_setext_heading_source_trims_paragraph_parts() -> None:
    text = '  Alpha\n  Beta  \n---\n'
    source = SourceMap.from_parts([('  Alpha\n', 100), ('  Beta  \n', 200), ('---\n', 300)])

    assert nested_setext_probe_positions(text, source) == [
        ('probe_A', 102, 103),
        ('probe_l', 103, 104),
        ('probe_p', 104, 105),
        ('probe_h', 105, 106),
        ('probe_a', 106, 107),
        ('probe_B', 202, 203),
        ('probe_e', 203, 204),
        ('probe_t', 204, 205),
        ('probe_a', 205, 206),
    ]


def test_wenmode_iterable_setext_heading_source_trims_paragraph_parts() -> None:
    root = Wenmode([SetextHeading, ProbeLetter], positions=True).parse(iter(['  Alpha\n', '  Beta  \n', '---\n']))
    heading = root.children[0]

    assert [
        (child.type, child.position.start if child.position is not None else None, child.position.end if child.position else None)
        for child in heading.children
        if child.type.startswith('probe_')
    ] == [
        ('probe_A', 2, 3),
        ('probe_l', 3, 4),
        ('probe_p', 4, 5),
        ('probe_h', 5, 6),
        ('probe_a', 6, 7),
        ('probe_B', 10, 11),
        ('probe_e', 11, 12),
        ('probe_t', 12, 13),
        ('probe_a', 13, 14),
    ]


def test_wenmode_collected_noncontiguous_source_maps_inline_positions() -> None:
    class SplitSourceRule(BlockRule):
        name = 'split_source'
        pattern = r'::split '

        def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
            line = state.line
            first_start = line.index('alpha')
            code_start = line.index('`beta`')
            source = state.source.collect()
            source.add(state.index, first_start, 'alpha ')
            source.add(state.index, code_start, '`beta`')
            state.advance()
            return BoxNode([Paragraph(children=parser.parse_inlines('alpha `beta`', state, source=source.map()))])

    root = Wenmode([SplitSourceRule, InlineCode], positions=True).parse('::split alpha ---- `beta`\n').to_ast()

    assert root['children'][0]['children'][0]['children'][1] == {
        'type': 'inlineCode',
        'position': {'start': {'line': 1, 'column': 20, 'offset': 19}, 'end': {'line': 1, 'column': 26, 'offset': 25}},
        'value': 'beta',
    }


def test_wenmode_iterable_source_positions_use_stream_tracker() -> None:
    root = Wenmode([ProbeLetter], positions=True).parse(iter(['a\n', 'b\n']))
    paragraph = root.children[0]

    assert [
        (child.type, child.position.start, child.position.end)
        for child in paragraph.children
        if child.type.startswith('probe_')
    ] == [
        ('probe_a', 0, 1),
        ('probe_b', 2, 3),
    ]
