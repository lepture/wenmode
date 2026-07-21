from __future__ import annotations

import time
from collections.abc import Callable, Iterable
from typing import Any

from wenmode import Wenmode
from wenmode.plugins import (
    abbr,
    block_math,
    definition_list,
    fenced_directive,
    html_container,
    inline_math,
    inline_spoiler,
    mark,
)
from wenmode.presets import commonmark, github
from wenmode.rules import (
    AtxHeading,
    ExtendedAutolink,
    Footnote,
    HardBreak,
    HtmlBlock,
    InlineCode,
    LeafDirective,
    Link,
    List,
    Rule,
    Table,
    TextDirective,
    ThematicBreak,
)


def parse_time(
    markdown: str, rules: Iterable[type[Rule] | Rule], plugins: Iterable[Any] = (), positions: bool = False
) -> float:
    parser = Wenmode(rules, positions=positions)
    for plugin in plugins:
        parser.use(plugin)
    started = time.perf_counter()
    parser.parse(markdown)
    return time.perf_counter() - started


def assert_scales_nearly_linearly(
    factory: Callable[[int], str],
    rules: Iterable[type[Rule] | Rule],
    small_size: int = 4000,
    large_size: int = 8000,
    plugins: Iterable[Any] = (),
    ratio: float = 3.5,
    slack: float = 0.02,
    positions: bool = False,
) -> None:
    small = parse_time(factory(small_size), rules, plugins, positions=positions)
    large = parse_time(factory(large_size), rules, plugins, positions=positions)

    assert large < small * ratio + slack


def test_unmatched_link_openers_do_not_rescan_suffixes() -> None:
    assert_scales_nearly_linearly(lambda size: '[' * size + '\n', commonmark)


def test_nested_link_label_brackets_do_not_parse_labels_recursively() -> None:
    assert_scales_nearly_linearly(lambda size: '[' * size + 'a' + ']' * size + '(/u)\n', commonmark, 200, 400)


def test_balanced_link_label_brackets_without_destination_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '[' * size + 'a' + ']' * size + '\n', commonmark, 1000, 2000)


def test_repeated_link_suffixes_do_not_rescan_outer_labels() -> None:
    assert_scales_nearly_linearly(lambda size: '[' * size + 'a' + '](/u)' * size + '\n', commonmark, 500, 1000)


def test_nested_image_alt_brackets_do_not_parse_unbounded_recursively() -> None:
    assert_scales_nearly_linearly(lambda size: '![' * size + 'a' + '](/u)' * size + '\n', commonmark, 200, 400)


def test_malformed_image_labels_without_destinations_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '![' * size + 'a' + ']' * size + '\n', commonmark, 1000, 2000)


def test_repeated_empty_label_unclosed_destinations_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '[](' * size + '\n', commonmark, 1000, 2000)


def test_failed_footnote_like_links_do_not_rescan_suffixes() -> None:
    assert_scales_nearly_linearly(lambda size: '[^x' * size + '\n', github)


def test_dense_emphasis_delimiters_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '*a' * size + '\n', commonmark)


def test_flat_mixed_emphasis_delimiters_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '*a_b' * size + '\n', commonmark, 1000, 2000)


def test_unmatched_code_span_runs_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '`' * size + 'text' + '`' * (size - 1) + '\n',
        [InlineCode],
        20000,
        40000,
        ratio=2.5,
        slack=0.005,
    )


def test_link_label_code_span_runs_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '[' + '`' * size + 'text' + '`' * (size - 1) + '](/url)\n',
        [Link],
        20000,
        40000,
        ratio=2.5,
        slack=0.005,
    )


def test_deep_blockquotes_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '> ' * size + 'text\n', commonmark, 1000, 2000)


def test_deep_lists_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '- ' * size + 'text\n', commonmark, 1000, 2000)


def test_plain_text_inline_dispatch_scales_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: 'a' * size + '\n', commonmark, 8000, 16000)


def test_repeated_hard_break_dispatch_scales_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: 'a  \n' * size, commonmark, 4000, 8000, ratio=3.0, slack=0.01)


def test_positioned_hard_breaks_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: 'a  \n' * size, [HardBreak], 2000, 4000, positions=True)


def test_leaf_directive_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '::a' + ' ' * size + 'x\n', [LeafDirective], 8000, 16000)


def test_atx_heading_closing_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '# ' + 'a' * size + ' ' * size + '#' * size + 'x\n', [AtxHeading], 2000, 4000
    )


def test_complete_html_tag_attributes_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '<custom data-x="' + 'x' * size + '">\n\n', [HtmlBlock], 8000, 16000)


def test_table_opener_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: 'a|' + 'x' * size + '\n', [Table], 8000, 16000)


def test_thematic_break_failed_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '* ' * size + 'x\n', [ThematicBreak], 1000, 2000)


def test_nested_html_block_raw_tags_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '<div>\n<pre>\n' + 'a\n' * size + '</pre>\n</div>\n', [HtmlBlock])


def test_disallowed_nested_html_filter_scales_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '<div>\n<script>\n' + 'alert(1)\n' * size + '</script>\n</div>\n',
        [HtmlBlock(disallowed_tags=['script'])],
        1000,
        2000,
    )


def test_inline_spoiler_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '>!x' + ' ' * size + 'y\n', [], 8000, 16000, plugins=[inline_spoiler])


def test_inline_math_invalid_digit_closers_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '$x' + '$5' * size + '\n', [], 500, 1000, plugins=[inline_math])


def test_declarative_inline_invalid_closers_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '==x ' * size + '==' * size + '\n', [], 500, 1000, plugins=[mark])


def test_text_directive_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: ':name[' * size + '\n', [TextDirective], 1000, 2000)


def test_nested_text_directives_do_not_parse_unbounded_recursively() -> None:
    assert_scales_nearly_linearly(lambda size: ':x[' * size + 'a' + ']' * size + '\n', [TextDirective], 200, 400)


def test_extended_autolink_trailing_parentheses_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: 'https://example.com/' + ')' * size + '\n', [ExtendedAutolink], 8000, 16000
    )


def test_unclosed_multiline_reference_title_scales_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '[x]: /url "\n' + 'a\n' * size + '\n[x]\n', [Link], 1000, 2000)


def test_unclosed_inline_link_title_escapes_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '[x](/url "' + '\\!' * size + '\n', [Link], 4000, 8000)


def test_many_reference_definitions_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: ''.join(f'[x{index}]: /url\n' for index in range(size)), [Link])


def test_footnote_blank_continuations_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '[^x]: first\n' + '\n' * size + '  second\n\n[^x]\n', [Footnote], 1000, 2000
    )


def test_list_blank_continuations_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '- a\n' + '\n' * size + '  b\n', [List], 1000, 2000)


def test_list_marker_interrupt_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: 'paragraph\n1. ' + ' ' * size + '\n', [List], 8000, 16000)


def test_list_marker_interrupt_candidates_with_positions_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: 'paragraph\n1. ' + ' ' * size + '\n',
        [List],
        8000,
        16000,
        positions=True,
    )


def test_abbreviation_definition_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '*[' + 'A' * size + '\n', [], 8000, 16000, plugins=[abbr])


def test_definition_description_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: 'Term\n: ' + ' ' * size + '\n', [], 8000, 16000, plugins=[definition_list]
    )


def test_fenced_directive_attribute_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '```{note}\n:class:' + ' ' * size + '\n```\n', [], 8000, 16000, plugins=[fenced_directive]
    )


def test_math_block_opener_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '$$ ' + ' ' * size + '\n$$\n', [], 8000, 16000, plugins=[block_math])


def test_html_container_long_attributes_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '<div data-x="' + 'x' * size + '">\n</div>\n', [], 8000, 16000, plugins=[html_container]
    )


def test_html_container_unclosed_candidates_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(lambda size: '<div>\n' + 'a\n' * size, [], plugins=[html_container])


def test_html_container_nested_same_name_tags_scale_nearly_linearly() -> None:
    assert_scales_nearly_linearly(
        lambda size: '<div>\n' * size + '</div>\n' * size, [], 64, 128, plugins=[html_container]
    )
