from __future__ import annotations

from wenmode import Wenmode
from wenmode.rules import AtxHeading, SetextHeading


def test_heading_id_transform_adds_heading_ids() -> None:
    app = Wenmode([AtxHeading(id_transform=True)])

    assert app.render('## Intro\n\n## Intro\n') == ('<h2 id="intro">Intro</h2>\n<h2 id="intro-1">Intro</h2>\n')


def test_heading_id_transform_dedupes_atx_and_setext_headings() -> None:
    app = Wenmode([AtxHeading(id_transform=True), SetextHeading(id_transform=True)])

    assert app.render('# Intro\n\nIntro\n-----\n') == ('<h1 id="intro">Intro</h1>\n<h2 id="intro-1">Intro</h2>\n')


def test_heading_id_transform_uses_fresh_slugger_per_parse() -> None:
    app = Wenmode([AtxHeading(id_transform=True)])

    assert app.render('## Intro\n') == '<h2 id="intro">Intro</h2>\n'
    assert app.render('## Intro\n') == '<h2 id="intro">Intro</h2>\n'
