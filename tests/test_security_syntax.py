from __future__ import annotations

import pytest

from wenmode import Wenmode
from wenmode.rules.inlines.link import parse_title
from wenmode.rules.references import parse_reference
from wenmode.state import BlockState
from wenmode.utils.text import parse_bare_destination


@pytest.mark.parametrize(
    'title', ['(a(b)', '(a\nb(c)', '(a\n \nb)', '(a\n' + ' \t' * 100 + '\nb)', '"a\n\nb"', "'a\r\n \r\nb'"]
)
def test_link_titles_reject_invalid_parentheses_and_blank_lines(title: str) -> None:
    assert parse_title(title, 0) is None


def test_link_titles_accept_escaped_parentheses_and_single_line_endings() -> None:
    assert parse_title(r'(a\(b)', 0) == ('a(b', 6)
    assert parse_title('"a\r\nb"', 0) == ('a\r\nb', 6)


@pytest.mark.parametrize('label', ['é' * 999, 'a' * 498 + '\n' + '界' * 500, r'\[' + 'x' * 997])
def test_reference_labels_allow_999_source_characters(label: str) -> None:
    state = BlockState(('[' + label + ']: /ok\n').splitlines(keepends=True))
    assert parse_reference(state, 0) is not None


@pytest.mark.parametrize(
    'label', ['é' * 1000, 'a' * 499 + '\n' + '界' * 500, r'\[' + 'x' * 998, 'a[b', 'a]b', 'a\n[b', 'a]\nb']
)
def test_reference_labels_reject_overlong_or_unescaped_brackets(label: str) -> None:
    state = BlockState(('[' + label + ']: /bad\n').splitlines(keepends=True))
    assert parse_reference(state, 0) is None


def test_invalid_reference_prefix_keeps_following_definition_and_heading() -> None:
    html = Wenmode().render('[bad\n# heading\n[good]: /ok\n\n[good]\n')
    assert '<h1>heading</h1>' in html
    assert html.endswith('<p><a href="/ok">good</a></p>\n')


def test_parenthesized_reference_title_rejects_unescaped_opening_parenthesis() -> None:
    state = BlockState(['[a]: /u (first\n', '[b]: /v (\n', 'last)\n'])
    assert parse_reference(state, 0) is None


@pytest.mark.parametrize('depth', [3, 20])
def test_bare_destination_supports_bounded_nested_parentheses(depth: int) -> None:
    url = '(' * depth + 'u' + ')' * depth
    assert parse_bare_destination(url, 0) == (url, len(url))


def test_bare_destination_rejects_more_than_twenty_nested_parentheses() -> None:
    assert parse_bare_destination('(' * 21 + 'u' + ')' * 21, 0) == (None, 0)
    url = r'\(' * 30 + 'u' + r'\)' * 30
    assert parse_bare_destination(url, 0) == (url, len(url))


def test_malformed_link_title_does_not_hide_following_valid_link() -> None:
    assert '<a href="/ok">good</a>' in Wenmode().render('[a](u (bad(open) [good](/ok)')


@pytest.mark.parametrize('ending', ['\n', '\r', '\r\n'])
def test_reference_label_limit_counts_normalized_line_endings(ending: str) -> None:
    label = 'a' * 498 + ending + 'b' * 500
    markdown = '[' + label + ']: /ok' + ending + ending + '[' + label + ']' + ending
    assert '<a href="/ok">' in Wenmode().render(markdown)


def test_reference_label_length_is_checked_before_entity_decoding() -> None:
    label = '&amp;' * 200
    assert '<a href=' not in Wenmode().render('[' + label + ']: /bad\n\n[' + label + ']\n')


@pytest.mark.parametrize('image', [False, True])
def test_full_references_allow_arbitrary_display_text_lengths(image: bool) -> None:
    label = 'a' * 3000
    markdown = ('!' if image else '') + '[' + label + '][x]\n\n[x]: /u\n'
    expected = '<p><img src="/u" alt="' + label + '" /></p>\n' if image else '<p><a href="/u">' + label + '</a></p>\n'
    assert Wenmode().render(markdown) == expected


@pytest.mark.parametrize('length', [999, 1000])
@pytest.mark.parametrize('kind', ['full', 'collapsed', 'shortcut'])
def test_inline_reference_label_source_limit_precedes_whitespace_normalization(length: int, kind: str) -> None:
    label = 'x' + ' ' * (length - 1)
    if kind == 'full':
        markdown = '[display][' + label + ']'
        display = 'display'
    else:
        markdown = '[' + label + ']' + ('[]' if kind == 'collapsed' else '')
        display = label
    html = Wenmode().render(markdown + '\n\n[x]: /u\n')
    expected = '<p><a href="/u">' + display + '</a></p>\n' if length == 999 else '<p>' + markdown + '</p>\n'
    assert html == expected
