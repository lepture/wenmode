from __future__ import annotations

from io import StringIO

import pytest

from wenmode import StreamingUnsupportedError, Wenmode
from wenmode.presets import commonmark, github, streaming
from wenmode.rules import Footnote, Link, List, Table


def lines(markdown: str):
    yield from markdown.splitlines(keepends=True)


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
