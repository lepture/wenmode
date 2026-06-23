from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from typing import Any

from wenmode import Wenmode
from wenmode.plugins import abbr, definition_list, fenced_directive, math, spoiler
from wenmode.presets import commonmark, github
from wenmode.rules import AtxHeading, ExtendedAutolink, Footnote, LeafDirective, Link, List, Rule, TextDirective


def parse_time(markdown: str, rules: list[type[Rule] | Rule], plugins: Iterable[Any] = ()) -> float:
    parser = Wenmode(rules)
    for plugin in plugins:
        parser.use(plugin)
    started = time.perf_counter()
    parser.parse(markdown)
    return time.perf_counter() - started


def assert_scales_nearly_linearly(
    factory: Callable[[int], str],
    rules: list[type[Rule] | Rule],
    small_size: int = 4000,
    large_size: int = 8000,
    plugins: Iterable[Any] = (),
) -> None:
    small = parse_time(factory(small_size), rules, plugins)
    large = parse_time(factory(large_size), rules, plugins)

    assert large < small * 3.5 + 0.02


def test_unmatched_link_openers_do_not_rescan_suffixes() -> None:
    assert_scales_nearly_linearly(lambda size: '[' * size + '\n', commonmark)


def test_failed_footnote_like_links_do_not_rescan_suffixes() -> None:
    assert_scales_nearly_linearly(lambda size: '[^x' * size + '\n', github)


def test_dense_emphasis_delimiters_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '*a' * size + '\n', commonmark)


def test_leaf_directive_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '::a' + ' ' * size + 'x\n', [LeafDirective], 8000, 16000)


def test_atx_heading_closing_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '# ' + 'a' * size + ' ' * size + '#' * size + 'x\n',
        [AtxHeading],
        2000,
        4000,
    )


def test_inline_spoiler_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '>!x' + ' ' * size + 'y\n', [], 8000, 16000, plugins=[spoiler])


def test_text_directive_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: ':name[' * size + '\n', [TextDirective], 1000, 2000)


def test_extended_autolink_trailing_parentheses_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: 'https://example.com/' + ')' * size + '\n',
        [ExtendedAutolink],
        8000,
        16000,
    )


def test_unclosed_multiline_reference_title_scales_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '[x]: /url "\n' + 'a\n' * size + '\n[x]\n', [Link], 1000, 2000)


def test_footnote_blank_continuations_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '[^x]: first\n' + '\n' * size + '  second\n\n[^x]\n',
        [Footnote],
        1000,
        2000,
    )


def test_list_blank_continuations_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '- a\n' + '\n' * size + '  b\n', [List], 1000, 2000)


def test_list_marker_interrupt_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: 'paragraph\n1. ' + ' ' * size + '\n', [List], 8000, 16000)


def test_abbreviation_definition_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '*[' + 'A' * size + '\n', [], 8000, 16000, plugins=[abbr])


def test_definition_description_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: 'Term\n: ' + ' ' * size + '\n',
        [],
        8000,
        16000,
        plugins=[definition_list],
    )


def test_fenced_directive_attribute_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '```{note}\n:class:' + ' ' * size + '\n```\n',
        [],
        8000,
        16000,
        plugins=[fenced_directive],
    )


def test_math_block_opener_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '$$ ' + ' ' * size + '\n$$\n', [], 8000, 16000, plugins=[math])
