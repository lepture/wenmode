from __future__ import annotations

import pytest

from wenmode import HTMLRenderer, Wenmode
from wenmode.presets import commonmark


def _render(markdown: str) -> str:
    parser = Wenmode(commonmark, HTMLRenderer(escape=False, sanitize_urls=False))
    return parser.render(markdown)


@pytest.mark.parametrize(
    ('markdown', 'html'),
    [
        # A combining mark (general category Mn) is not Unicode punctuation per the
        # CommonMark 0.31.2 flanking rules, so emphasis adjacent to one must still apply.
        # "cafe" + U+0301 COMBINING ACUTE ACCENT, then a letter.
        ('**café**s\n', '<p><strong>café</strong>s</p>\n'),
        ('a*́foo*\n', '<p>a<em>́foo</em></p>\n'),
        # A zero-width joiner (U+200D, general category Cf) is likewise not punctuation.
        ('*foo‍*bar\n', '<p><em>foo‍</em>bar</p>\n'),
        # Regression guard: an intraword underscore next to a combining mark must NOT
        # open emphasis (the mark counts as an ordinary character, not punctuation).
        ('a_́foo_\n', '<p>a_́foo_</p>\n'),
    ],
)
def test_emphasis_flanking_excludes_marks_and_format_chars(markdown: str, html: str) -> None:
    assert _render(markdown) == html
