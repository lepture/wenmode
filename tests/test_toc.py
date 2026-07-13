from __future__ import annotations

from wenmode import Wenmode
from wenmode.headings import HeadingIdTransform
from wenmode.plugins import heading_ids
from wenmode.rules import AtxHeading, SetextHeading
from wenmode.toc import render_toc_html


def test_heading_id_transform_adds_heading_ids() -> None:
    app = Wenmode([AtxHeading(transforms=[HeadingIdTransform()])])

    assert app.render('## Intro\n\n## Intro\n') == '<h2 id="intro">Intro</h2>\n<h2 id="intro-1">Intro</h2>\n'


def test_heading_id_transform_dedupes_atx_and_setext_headings() -> None:
    transform = HeadingIdTransform()
    app = Wenmode([AtxHeading(transforms=[transform]), SetextHeading(transforms=[transform])])

    assert app.render('# Intro\n\nIntro\n-----\n') == '<h1 id="intro">Intro</h1>\n<h2 id="intro-1">Intro</h2>\n'


def test_heading_id_transform_uses_fresh_slugger_per_parse() -> None:
    app = Wenmode([AtxHeading(transforms=[HeadingIdTransform()])])

    assert app.render('## Intro\n') == '<h2 id="intro">Intro</h2>\n'
    assert app.render('## Intro\n') == '<h2 id="intro">Intro</h2>\n'


def test_heading_ids_plugin_adds_ids_to_enabled_heading_rules() -> None:
    app = Wenmode([AtxHeading, SetextHeading], plugins=[heading_ids])

    assert app.render('# Intro\n\nIntro\n-----\n') == '<h1 id="intro">Intro</h1>\n<h2 id="intro-1">Intro</h2>\n'


def test_heading_ids_plugin_does_not_enable_missing_heading_rules() -> None:
    app = Wenmode([AtxHeading], plugins=[heading_ids])

    assert app.render('# Intro\n\nIntro\n-----\n') == '<h1 id="intro">Intro</h1>\n<p>Intro\n-----</p>\n'


def test_heading_ids_plugin_does_not_duplicate_existing_transform() -> None:
    app = Wenmode([AtxHeading(transforms=[HeadingIdTransform()])], plugins=[heading_ids])

    assert app.render('# Intro\n\n# Intro\n') == '<h1 id="intro">Intro</h1>\n<h1 id="intro-1">Intro</h1>\n'


def test_render_empty_toc_html() -> None:
    assert render_toc_html([]) == ''
