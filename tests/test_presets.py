from __future__ import annotations

import pytest

from wenmode import Parser, Wenmode
from wenmode.presets import GFM_DISALLOWED_HTML_TAGS, commonmark, create_preset, github, streaming
from wenmode.rules import AtxHeading, HtmlBlock, Image, Link, RawHtml, Strikethrough


def test_create_preset_removes_and_replaces_rules_by_name() -> None:
    preset = create_preset(
        commonmark(),
        remove=[HtmlBlock, RawHtml],
        replace=[Link(references=False), Image(references=False)],
        append=[Strikethrough],
    )

    app = Wenmode(preset)

    assert app.render('<span>text</span>\n') == '<p>&lt;span&gt;text&lt;/span&gt;</p>\n'
    assert app.render('[x]: /url\n\n[x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n'
    assert app.render('[x](/url) and ~~old~~\n') == '<p><a href="/url">x</a> and <del>old</del></p>\n'


def test_create_preset_keeps_replacements_at_original_position() -> None:
    preset = create_preset(commonmark(), replace=[Link(references=False)])
    names = [rule.name if not isinstance(rule, type) else rule.name for rule in preset]

    commonmark_rule_names = [rule.name for rule in commonmark()]
    assert names.index('link') == commonmark_rule_names.index('link')


def test_create_preset_supports_prepend_and_append() -> None:
    preset = create_preset([], prepend=[AtxHeading], append=[Link])

    assert Wenmode(preset).render('# Title\n\n[link](/url)\n') == '<h1>Title</h1>\n<p><a href="/url">link</a></p>\n'


def test_create_preset_rejects_missing_replacements() -> None:
    with pytest.raises(ValueError, match='cannot replace rules that are not in the base preset: strikethrough'):
        create_preset(commonmark(), replace=[Strikethrough])


def test_create_preset_rejects_duplicate_replacements() -> None:
    with pytest.raises(ValueError, match='duplicate replacement rule: link'):
        create_preset(commonmark(), replace=[Link, Link(references=False)])


@pytest.mark.parametrize('preset', [GFM_DISALLOWED_HTML_TAGS, commonmark(), streaming(), github()])
def test_builtin_presets_are_read_only(preset: tuple[object, ...]) -> None:
    with pytest.raises(AttributeError):
        preset.append(object())
    with pytest.raises(TypeError):
        preset[0] = object()


def test_create_preset_returns_a_mutable_copy() -> None:
    preset = create_preset(commonmark())

    preset.append(Strikethrough)

    assert preset[-1] is Strikethrough
    assert Strikethrough not in commonmark()


@pytest.mark.parametrize('factory', [commonmark, streaming, github])
def test_preset_factories_create_isolated_parser_rules(factory) -> None:
    first = Wenmode(factory()).parser.rules
    second = Wenmode(factory()).parser.rules

    assert first.keys() == second.keys()
    assert all(first[name] is not second[name] for name in first)


def test_wenmode_accepts_deprecated_preset_factory() -> None:
    with pytest.warns(DeprecationWarning, match=r'use github\(\) instead') as caught:
        Wenmode(github)

    assert caught[0].filename == __file__


def test_parser_accepts_deprecated_preset_factory() -> None:
    with pytest.warns(DeprecationWarning, match=r'use commonmark\(\) instead') as caught:
        Parser(commonmark)

    assert caught[0].filename == __file__


def test_create_preset_accepts_deprecated_preset_factory() -> None:
    with pytest.warns(DeprecationWarning, match=r'use streaming\(\) instead') as caught:
        create_preset(streaming)

    assert caught[0].filename == __file__
