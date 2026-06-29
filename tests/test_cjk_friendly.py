from __future__ import annotations

from wenmode import Wenmode
from wenmode.plugins import cjk_friendly
from wenmode.presets import github


def test_cjk_friendly_parses_strong_before_cjk_text() -> None:
    source = '**你好。**世界\n'

    assert Wenmode().render(source) == '<p>**你好。**世界</p>\n'
    assert Wenmode(plugins=[cjk_friendly]).render(source) == '<p><strong>你好。</strong>世界</p>\n'


def test_cjk_friendly_parses_strong_after_cjk_text() -> None:
    source = '世界**（你好**\n'

    assert Wenmode().render(source) == '<p>世界**（你好**</p>\n'
    assert Wenmode(plugins=[cjk_friendly]).render(source) == '<p>世界<strong>（你好</strong></p>\n'


def test_cjk_friendly_keeps_non_cjk_commonmark_behavior() -> None:
    source = 'a**(b**\n'

    assert Wenmode().render(source) == '<p>a**(b**</p>\n'
    assert Wenmode(plugins=[cjk_friendly]).render(source) == '<p>a**(b**</p>\n'


def test_cjk_friendly_keeps_intraword_underscore_restriction() -> None:
    source = '_你好。_世界\n'

    assert Wenmode().render(source) == '<p>_你好。_世界</p>\n'
    assert Wenmode(plugins=[cjk_friendly]).render(source) == '<p>_你好。_世界</p>\n'


def test_cjk_friendly_trims_cjk_punctuation_from_extended_autolinks() -> None:
    source = '请看 https://example.com/path。\n'

    assert Wenmode(github).render(source) == (
        '<p>请看 <a href="https://example.com/path%E3%80%82">https://example.com/path。</a></p>\n'
    )
    assert Wenmode(github, plugins=[cjk_friendly]).render(source) == (
        '<p>请看 <a href="https://example.com/path">https://example.com/path</a>。</p>\n'
    )


def test_cjk_friendly_does_not_enable_extended_autolinks() -> None:
    source = '请看 https://example.com/path。\n'

    assert Wenmode(plugins=[cjk_friendly]).render(source) == '<p>请看 https://example.com/path。</p>\n'
