from __future__ import annotations

from io import StringIO

import pytest

from wenmode import StreamingUnsupportedError, Wenmode
from wenmode.headings import HeadingIdTransform
from wenmode.nodes import Node, Position
from wenmode.parser import Parser
from wenmode.presets import commonmark, github, streaming
from wenmode.rules import AtxHeading, BlockCandidate, BlockRule, Footnote, Image, Link, List, RootTransform, Rule, Table
from wenmode.state import StreamBlockState, StreamLineBuffer


def lines(markdown: str):
    yield from markdown.splitlines(keepends=True)


class OneLineProbeRule(BlockRule):
    name = 'one_line_probe'
    pattern = r'^!'

    def __init__(self) -> None:
        super().__init__()
        self.states: list[StreamBlockState] = []

    def parse(self, parser, state, candidate: BlockCandidate) -> Node | None:
        assert isinstance(state, StreamBlockState)
        self.states.append(state)
        state.advance()
        return Node(type='probe')


class LookaheadProbeRule(BlockRule):
    name = 'lookahead_probe'
    pattern = r'^\?'

    def __init__(self) -> None:
        super().__init__()
        self.states: list[StreamBlockState] = []

    def parse(self, parser, state, candidate: BlockCandidate) -> Node | None:
        if isinstance(state, StreamBlockState):
            self.states.append(state)
        if state.has(1):
            state.peek(1)
        state.advance()
        return Node(type='lookaheadProbe')


class LocalRootTransform(RootTransform):
    name = 'local_root'


class LocalRootTransformRule(Rule):
    name = 'local_root_rule'

    def __init__(self) -> None:
        super().__init__()
        self.root_transforms = [LocalRootTransform()]


def large_probe_lines(count: int):
    for index in range(count):
        yield f'!{index:05d} ' + ('x' * 2048) + '\n'


def test_parser_accepts_synchronous_text_streams() -> None:
    app = Wenmode(github)
    markdown = '# Title\n\nA [link][x] and a note[^one].\n\n[x]: /url\n[^one]: note\n'
    expected = app.render(markdown)

    assert app.render(StringIO(markdown)) == expected
    assert app.render(markdown.splitlines(keepends=True)) == expected
    assert app.render(lines(markdown)) == expected


def test_stream_reference_definition_can_affect_earlier_blocks() -> None:
    app = Wenmode([Link])
    markdown = '[x]\n\n[x]: /url "ti\ntle"\n'

    assert app.render(lines(markdown)) == '<p><a href="/url" title="ti\ntle">x</a></p>\n'


def test_stream_table_lookahead() -> None:
    app = Wenmode([Table])
    markdown = '| a | b |\n| --- | --- |\n| c | d |\n'

    assert app.render(lines(markdown)) == app.render(markdown)


def test_stream_line_buffer_discards_consumed_one_line_blocks() -> None:
    rule = OneLineProbeRule()
    parser = Wenmode([rule]).parser
    total = 3000

    for index, node in enumerate(parser.parse_iter(large_probe_lines(total))):
        assert node.type == 'probe'
        state = rule.states[-1]
        buffer = state.line_buffer
        assert state.index == index + 1
        assert buffer.start_index == index + 1
        assert buffer.lines == []

    state = rule.states[-1]
    assert state.index == total
    assert state.line_buffer.start_index == total
    assert state.line_buffer.lines == []


def test_positioned_stream_compaction_preserves_absolute_offsets() -> None:
    rule = OneLineProbeRule()
    parser = Wenmode([rule], positions=True).parser
    total = 3000
    line_length = len('!00000 ' + ('x' * 2048) + '\n')
    observed: dict[int, Position] = {}

    for index, node in enumerate(parser.parse_iter(large_probe_lines(total))):
        if index in {0, total // 2, total - 1}:
            assert node.position is not None
            observed[index] = node.position
        state = rule.states[-1]
        assert state.line_buffer.lines == []
        assert state.line_buffer.line_offsets == []

    assert observed == {
        0: Position(start=0, end=line_length),
        total // 2: Position(start=(total // 2) * line_length, end=((total // 2) + 1) * line_length),
        total - 1: Position(start=(total - 1) * line_length, end=total * line_length),
    }
    state = rule.states[-1]
    assert state.line_buffer.lines == []
    assert state.line_buffer.line_offsets == []


def test_stream_compaction_preserves_prefetched_lookahead() -> None:
    rule = LookaheadProbeRule()
    parser = Wenmode([rule]).parser
    markdown = '?a\n?b\n?c\n'
    stream = parser.parse_iter(lines(markdown))

    first = next(stream)
    first_state = rule.states[0]
    assert first_state.line_buffer.start_index == 1
    assert first_state.line_buffer.lines == ['?b\n']

    streamed = [first.to_ast(), *(node.to_ast() for node in stream)]
    full = [node.to_ast() for node in parser.parse(markdown).children]

    assert streamed == full


def test_stream_line_buffer_absolute_window_and_offsets() -> None:
    source = (f'{index}\n' for index in range(14))
    buffer = StreamLineBuffer(source, track_positions=True)

    assert buffer.has(12) is True
    assert buffer.start_index == 0
    assert buffer.get(0) == '0\n'
    assert buffer.get(12) == '12\n'

    original_lines = buffer.lines
    original_offsets = buffer.line_offsets
    buffer.discard_before(10)
    assert buffer.lines is original_lines
    assert buffer.line_offsets is original_offsets
    assert buffer.start_index == 10
    assert buffer.lines == ['10\n', '11\n', '12\n']
    assert buffer.line_offsets == [20, 23, 26]

    buffer.discard_before(11)
    assert buffer.start_index == 11
    assert buffer.get(11) == '11\n'
    assert buffer.get(12) == '12\n'
    assert buffer.get(13) == '13\n'
    assert buffer.lines == ['11\n', '12\n', '13\n']
    assert buffer.line_offsets == [23, 26, 29]
    with pytest.raises(IndexError, match='discarded'):
        buffer.get(10)


def test_stream_footnote_continuation_lookahead() -> None:
    app = Wenmode([Footnote])
    markdown = '[^one]: first\n\n  second\n\nA note[^one]\n'

    assert app.render(lines(markdown)) == app.render(markdown)


def test_stream_list_blank_line_lookahead() -> None:
    app = Wenmode([List])
    markdown = '- a\n\n  b\n- c\n'

    assert app.render(lines(markdown)) == app.render(markdown)


def test_streaming_preset_disables_references() -> None:
    app = Wenmode(streaming)

    assert 'reference_definition' not in app.parser.rules
    assert app.render('[x](/url) and ![alt](/img.png)\n') == (
        '<p><a href="/url">x</a> and <img src="/img.png" alt="alt" /></p>\n'
    )
    assert app.render('[x]: /url\n\n[x]\n\n![x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n<p>![x]</p>\n'


def test_wenmode_stream_matches_full_render_for_streaming_preset() -> None:
    wen = Wenmode(streaming)
    markdown = '# Title\n\nA [link](/url) and ~~old~~ text.\n\n| A | B |\n| --- | --- |\n| x | y |\n\n- one\n- two\n'

    assert ''.join(wen.stream(markdown)) == wen.render(markdown)
    assert ''.join(wen.stream(StringIO(markdown))) == wen.render(markdown)
    assert ''.join(wen.stream(lines(markdown))) == wen.render(markdown)


def test_streaming_preset_supports_table_and_strikethrough() -> None:
    html = Wenmode(streaming).render('| A | B |\n| --- | --- |\nx | ~~old~~\n')

    assert '<table>' in html
    assert '<td><del>old</del></td>' in html


def test_wenmode_stream_does_not_read_entire_input_before_first_chunk() -> None:
    consumed = 0

    def chunks():
        nonlocal consumed
        for line in ['# Title\n', '\n', 'Second paragraph.\n']:
            consumed += 1
            yield line

    stream = Wenmode(streaming).stream(chunks())

    assert next(stream) == '<h1>Title</h1>\n'
    assert consumed == 1


def test_wenmode_stream_rejects_unsupported_rules() -> None:
    with pytest.raises(StreamingUnsupportedError, match='reference'):
        next(Wenmode(commonmark).stream('[x]\n\n[x]: /url\n'))

    with pytest.raises(StreamingUnsupportedError, match='footnote, reference'):
        next(Wenmode(github).stream('a[^one]\n\n[^one]: note\n'))

    with pytest.raises(StreamingUnsupportedError, match='footnote'):
        next(Wenmode([Footnote]).stream('a[^one]\n\n[^one]: note\n'))


def test_parse_iter_supports_heading_id_node_transform() -> None:
    parser = Parser([AtxHeading(transforms=[HeadingIdTransform()]), Image(references=False)])

    assert parser.supports_streaming is True
    assert parser.streaming_blockers() == []
    assert [node.to_ast() for node in parser.parse_iter('# Title\n# Title\n')] == [
        {'type': 'heading', 'data': {'id': 'title'}, 'children': [{'type': 'text', 'value': 'Title'}], 'depth': 1},
        {'type': 'heading', 'data': {'id': 'title-1'}, 'children': [{'type': 'text', 'value': 'Title'}], 'depth': 1},
    ]

    expected_image = {'type': 'image', 'url': '/image.jpg', 'alt': 'alt', 'title': 'title'}
    assert [node.to_ast() for node in parser.parse_iter('# ![alt](/image.jpg "title")\n')] == [
        {'type': 'heading', 'data': {'id': 'alt'}, 'children': [expected_image], 'depth': 1},
    ]


def test_parse_iter_rejects_custom_non_deferred_root_transform() -> None:
    parser = Parser([LocalRootTransformRule])

    assert parser.supports_streaming is False
    assert parser.streaming_blockers() == ['local_root']
    with pytest.raises(StreamingUnsupportedError, match='parser transforms: local_root'):
        next(parser.parse_iter('Body\n'))


def test_parser_and_wenmode_report_streaming_support() -> None:
    streamable = Wenmode(streaming)
    full_document = Wenmode(github)

    assert streamable.supports_streaming is True
    assert streamable.parser.supports_streaming is True
    assert streamable.streaming_blockers() == []
    assert streamable.parser.streaming_blockers() == []

    assert full_document.supports_streaming is False
    assert full_document.parser.supports_streaming is False
    assert full_document.streaming_blockers() == ['footnote', 'reference']
    assert full_document.parser.streaming_blockers() == ['footnote', 'reference']
