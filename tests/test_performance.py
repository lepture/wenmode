from __future__ import annotations

import time
from collections.abc import Callable

from wenmode import Wenmode
from wenmode.presets import commonmark, github
from wenmode.rules import AtxHeading, ExtendedAutolink, InlineSpoiler, LeafDirective, Rule, TextDirective


def parse_time(markdown: str, rules: list[type[Rule] | Rule]) -> float:
    parser = Wenmode(rules)
    started = time.perf_counter()
    parser.parse(markdown)
    return time.perf_counter() - started


def assert_scales_nearly_linearly(
    factory: Callable[[int], str], rules: list[type[Rule] | Rule], small_size: int = 4000, large_size: int = 8000
) -> None:
    small = parse_time(factory(small_size), rules)
    large = parse_time(factory(large_size), rules)

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
    assert_scales_nearly_linearly(lambda size: '>!x' + ' ' * size + 'y\n', [InlineSpoiler], 8000, 16000)


def test_text_directive_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: ':name[' * size + '\n', [TextDirective], 1000, 2000)


def test_extended_autolink_trailing_parentheses_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: 'https://example.com/' + ')' * size + '\n',
        [ExtendedAutolink],
        8000,
        16000,
    )
