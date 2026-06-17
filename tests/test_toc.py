from __future__ import annotations

from wenmode import HTMLRenderer, Parser
from wenmode.headings import Slugger, add_heading_ids
from wenmode.presets import commonmark
from wenmode.rules import AtxHeading, HeadingIdTransform, SetextHeading
from wenmode.toc import collect_toc, render_toc_html


def test_add_heading_ids_and_collect_toc() -> None:
    root = Parser(commonmark).parse(
        '# Title\n\n'
        '## Usage & Setup!\n\n'
        '### Install `wenmode`\n\n'
        '## Usage & Setup!\n'
    )

    add_heading_ids(root, slugger=Slugger(), min_depth=2)
    toc = collect_toc(root, min_depth=2, max_depth=3)

    assert [item.id for item in toc] == ['usage-setup', 'usage-setup-1']
    assert toc[0].title == 'Usage & Setup!'
    assert toc[0].children[0].id == 'install-wenmode'
    assert HTMLRenderer().render(root).startswith('<h1>Title</h1>\n<h2 id="usage-setup">')


def test_collect_toc_uses_existing_heading_ids_without_overwriting() -> None:
    root = Parser(commonmark).parse('## Intro\n\n## Intro\n')
    first, second = root.children
    first.data = {'id': 'custom'}

    add_heading_ids(root, slugger=Slugger())
    toc = collect_toc(root)

    assert [item.id for item in toc] == ['custom', 'intro']
    assert second.data == {'id': 'intro'}


def test_render_toc_html_escapes_titles_and_ids() -> None:
    root = Parser(commonmark).parse('## A <B>\n\n### Child\n')
    root.children[0].data = {'id': 'a"<b>'}
    root.children[1].data = {'id': 'child'}
    toc = collect_toc(root)

    assert render_toc_html(toc) == (
        '<nav class="toc" aria-label="Table of contents">\n'
        '<ol>\n'
        '<li><a href="#a&quot;&lt;b&gt;">A &lt;B&gt;</a>\n'
        '<ol>\n'
        '<li><a href="#child">Child</a></li>\n'
        '</ol>\n'
        '</li>\n'
        '</ol>\n'
        '</nav>\n'
    )


def test_heading_id_transform_adds_heading_ids() -> None:
    parser = Parser([AtxHeading(id_transform=True)])

    assert HTMLRenderer().render(parser.parse('## Intro\n\n## Intro\n')) == (
        '<h2 id="intro">Intro</h2>\n'
        '<h2 id="intro-1">Intro</h2>\n'
    )


def test_heading_id_transform_dedupes_atx_and_setext_headings() -> None:
    parser = Parser([AtxHeading(id_transform=True), SetextHeading(id_transform=True)])

    assert [transform.name for transform in parser.root_transforms] == ['heading_id:default']
    assert HTMLRenderer().render(parser.parse('# Intro\n\nIntro\n-----\n')) == (
        '<h1 id="intro">Intro</h1>\n'
        '<h2 id="intro-1">Intro</h2>\n'
    )


def test_heading_id_transform_uses_fresh_slugger_per_parse() -> None:
    parser = Parser([AtxHeading(id_transform=True)])

    assert HTMLRenderer().render(parser.parse('## Intro\n')) == '<h2 id="intro">Intro</h2>\n'
    assert HTMLRenderer().render(parser.parse('## Intro\n')) == '<h2 id="intro">Intro</h2>\n'


def test_heading_id_transform_uses_slugger_factory_name() -> None:
    class CustomSlugger(Slugger):
        name = 'custom'

        def slug(self, value: str) -> str:
            return 'custom-' + super().slug(value)

    transform = HeadingIdTransform(CustomSlugger)
    parser = Parser([AtxHeading(id_transform=transform), SetextHeading(id_transform=transform)])

    assert [registered.name for registered in parser.root_transforms] == ['heading_id:custom']
    assert HTMLRenderer().render(parser.parse('## Intro\n')) == '<h2 id="custom-intro">Intro</h2>\n'
