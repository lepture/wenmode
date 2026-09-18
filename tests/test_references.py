from __future__ import annotations

import pytest

from wenmode import Wenmode
from wenmode.rules.references import parse_multiline_reference_title
from wenmode.state import BlockState


@pytest.mark.parametrize('opener', ['(', '"', "'"])
def test_failed_reference_titles_scan_each_continuation_once(opener: str, monkeypatch: pytest.MonkeyPatch) -> None:
    state = BlockState(['still open\n'] * 100)
    reads = 0
    line_at = BlockState.line_at

    def counted_line_at(self: BlockState, index: int) -> str:
        nonlocal reads
        reads += 1
        return line_at(self, index)

    monkeypatch.setattr(BlockState, 'line_at', counted_line_at)
    for index in range(100):
        assert parse_multiline_reference_title(opener + 'unfinished', state, index) == (None, 100)

    assert reads <= 100


def test_reference_title_failure_cache_does_not_hide_closer_on_first_line() -> None:
    state = BlockState(['unused\n', 'escaped\\)\n', 'still open\n'])

    assert parse_multiline_reference_title('(unfinished', state, 1) == (None, 3)
    assert parse_multiline_reference_title('(closed)', state, 1) == (('closed', ''), 1)


def test_reference_title_failure_cache_is_scoped_to_block_source() -> None:
    first = BlockState(['unused\n', 'still open\n', 'still open\n'])
    second = BlockState(['unused\n', 'closed)\n'], store=first.store)

    assert parse_multiline_reference_title('(unfinished', first, 1) == (None, 3)
    assert parse_multiline_reference_title('(new', second, 1) == (('new\nclosed', ''), 2)


def test_failed_reference_titles_do_not_hide_valid_titles_after_blank_line() -> None:
    markdown = '[bad]: /u (\n# h\n' * 3 + '\n[good]: /ok (multi\nline)\n\n[good]\n'
    app = Wenmode()

    html = app.render(markdown)

    assert html.endswith('<p><a href="/ok" title="multi\nline">good</a></p>\n')
    assert app.render(iter(markdown.splitlines(keepends=True))) == html


def test_multiline_reference_title_can_contain_definition_like_lines() -> None:
    markdown = '[a]: /u (first\n[b]: /v (\nlast)\n\n[a]\n'

    assert Wenmode().render(markdown) == '<p><a href="/u" title="first\n[b]: /v (\nlast">a</a></p>\n'


def test_reference_title_failure_cache_does_not_leak_between_documents() -> None:
    app = Wenmode()
    app.render('[bad]: /u (\n# h\n' * 3)

    assert app.render('[good]: /ok (multi\nline)\n\n[good]\n') == (
        '<p><a href="/ok" title="multi\nline">good</a></p>\n'
    )
