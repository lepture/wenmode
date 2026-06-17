from __future__ import annotations

import time
from collections.abc import Callable

from wenmode import Wenmode
from wenmode.presets import commonmark, github
from wenmode.rules.base import Rule


def parse_time(markdown: str, rules: list[type[Rule] | Rule]) -> float:
    parser = Wenmode(rules)
    started = time.perf_counter()
    parser.parse(markdown)
    return time.perf_counter() - started


def assert_scales_nearly_linearly(factory: Callable[[int], str], rules: list[type[Rule] | Rule]) -> None:
    small = parse_time(factory(4000), rules)
    large = parse_time(factory(8000), rules)

    assert large < small * 3.5 + 0.02


def test_unmatched_link_openers_do_not_rescan_suffixes() -> None:
    assert_scales_nearly_linearly(lambda size: '[' * size + '\n', commonmark)


def test_failed_footnote_like_links_do_not_rescan_suffixes() -> None:
    assert_scales_nearly_linearly(lambda size: '[^x' * size + '\n', github)


def test_dense_emphasis_delimiters_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '*a' * size + '\n', commonmark)
