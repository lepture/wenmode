from __future__ import annotations

import pytest

from wenmode import Parser, Wenmode
from wenmode.nodes import Parent
from wenmode.plugins import inline_spoiler
from wenmode.rules import InlineCode, Link
from wenmode.rules.inlines import code
from wenmode.state import BlockState


def test_code_and_link_bracket_scans_share_one_lazy_backtick_index(monkeypatch: pytest.MonkeyPatch) -> None:
    scans: list[tuple[int, int]] = []
    pattern = code.BACKTICK_RUN_RE

    class CountedRuns:
        def match(self, text: str, start: int):
            return pattern.match(text, start)

        def finditer(self, text: str, start: int = 0):
            scans.append((len(text), start))
            return pattern.finditer(text, start)

    monkeypatch.setattr(code, 'BACKTICK_RUN_RE', CountedRuns())
    parser = Parser([Link, InlineCode])
    markdown = '[label](/u) ' + 'x '.join('`' * length for length in range(1, 200))
    parser.parse_inlines(markdown, BlockState([]))
    # One initial failed search, then one index construction for both consumers.
    assert len(scans) == 2
    assert scans[-1] == (len(markdown), 0)
    parser.parse_inlines('`fresh`', BlockState([]))
    assert scans[-1] == (7, 1)
    assert len(scans) == 3


@pytest.mark.parametrize(
    'markdown, expected',
    [
        ('``a`b``', '<p><code>a`b</code></p>\n'),
        (r'`a\`', '<p><code>a\\</code></p>\n'),
        (r'\`a`', '<p>`a`</p>\n'),
        ('[a `]` b](/u)', '<p><a href="/u">a <code>]</code> b</a></p>\n'),
        ('[a ``]`` b](/u)', '<p><a href="/u">a <code>]</code> b</a></p>\n'),
    ],
)
def test_indexed_backticks_preserve_exact_length_escapes_and_bracket_precedence(markdown: str, expected: str) -> None:
    assert Wenmode().render(markdown) == expected


def test_arbitrary_backtick_run_lengths_remain_supported() -> None:
    marker = '`' * 2000
    assert Wenmode([InlineCode]).render('x ' + marker + 'a' + marker) == '<p>x <code>a</code></p>\n'


@pytest.mark.parametrize('ending', ['\n', '\r', '\r\n'])
@pytest.mark.parametrize('padding', ['', ' \t' * 20])
def test_spoiler_rejects_line_endings_even_when_they_would_be_trimmed(ending: str, padding: str) -> None:
    app = Wenmode([]).use(inline_spoiler)
    root = app.parse('x >!a' + ending + padding + '!<')
    assert not any(isinstance(child, Parent) for child in root.children[0].children)


def test_rejected_spoiler_openers_validate_each_escaped_closer_once(monkeypatch: pytest.MonkeyPatch) -> None:
    app = Wenmode([]).use(inline_spoiler)
    syntax = app.parser.rules['inline_spoiler']
    is_closer = syntax._is_closing_delimiter
    calls = 0

    def counted_closer(text: str, start: int) -> bool:
        nonlocal calls
        calls += 1
        return is_closer(text, start)

    monkeypatch.setattr(syntax, '_is_closing_delimiter', counted_closer)
    markdown = 'x >!a ' * 1000 + r'\!<' * 1000
    app.parse(markdown)
    assert calls == 1000


def test_late_spoiler_closer_after_rejected_openers_does_not_hide_valid_following_spoiler() -> None:
    app = Wenmode([]).use(inline_spoiler)
    markdown = 'x >!a ' * 1000 + '\nlate !< >!good!<'
    html = app.render(markdown)
    assert html.endswith('late !&lt; <span class="spoiler">good</span></p>\n')


def test_spoiler_trimmed_content_positions_stay_absolute() -> None:
    app = Wenmode([], positions=True).use(inline_spoiler)
    spoiler = app.parse('x >!  a  !<').children[0].children[1]
    assert spoiler.children[0].value == 'a'
    assert spoiler.children[0].position.start == 6
    assert spoiler.children[0].position.end == 7


class CountedText(str):
    reads = 0

    def __getitem__(self, key):
        if isinstance(key, int):
            self.reads += 1
        return super().__getitem__(key)


def test_invalid_parenthesized_title_candidates_read_a_bounded_prefix() -> None:
    from wenmode.rules.inlines.link import parse_title

    text = CountedText('[a](u (' * 1000)
    for start in range(6, len(text), 7):
        assert parse_title(text, start) is None
    assert text.reads < 10 * 1000


def test_unbalanced_destination_candidates_are_bounded_by_parenthesis_depth() -> None:
    from wenmode.utils.text import parse_bare_destination_result

    text = CountedText('[a](()' * 1000)
    for start in range(4, len(text) - 21 * 6, 6):
        assert parse_bare_destination_result(text, start)[0] is None
    assert text.reads < 150 * 1000


def test_failed_multiline_labels_do_not_revisit_the_document_tail(monkeypatch: pytest.MonkeyPatch) -> None:
    from wenmode.rules.references import parse_reference_label

    state = BlockState(['[a\n', '# h\n'] * 1000)
    reads = 0
    line_at = BlockState.line_at

    def counted_line_at(self: BlockState, index: int) -> str:
        nonlocal reads
        reads += 1
        return line_at(self, index)

    monkeypatch.setattr(BlockState, 'line_at', counted_line_at)
    for index in range(0, len(state.lines), 2):
        assert parse_reference_label(state, index) is None
    assert reads < 4 * 1000


def test_matching_code_spans_do_not_probe_an_empty_failure_index() -> None:
    class EmptyCache(dict):
        def get(self, key, default=None):
            raise AssertionError('an empty cache cannot contain a source index')

    cache = EmptyCache()
    assert code.find_matching_backtick_run('`a`', 1, 1, cache) == 2
    assert not cache
    assert code.find_matching_backtick_run('`a', 1, 1, cache) is None
    assert cache
    assert code.find_matching_backtick_run('`a', 1, 1, dict(cache)) is None
