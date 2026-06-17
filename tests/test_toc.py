from __future__ import annotations

from wenmode import HTMLRenderer, Parser, add_heading_ids, collect_toc, commonmark, render_toc_html


def test_add_heading_ids_and_collect_toc() -> None:
    root = Parser(commonmark).parse(
        '# Title\n\n'
        '## Usage & Setup!\n\n'
        '### Install `wenmode`\n\n'
        '## Usage & Setup!\n'
    )

    add_heading_ids(root, min_depth=2)
    toc = collect_toc(root, min_depth=2, max_depth=3)

    assert [item.id for item in toc] == ['usage-setup', 'usage-setup-1']
    assert toc[0].title == 'Usage & Setup!'
    assert toc[0].children[0].id == 'install-wenmode'
    assert HTMLRenderer().render(root).startswith('<h1>Title</h1>\n<h2 id="usage-setup">')


def test_collect_toc_uses_existing_heading_ids_without_overwriting() -> None:
    root = Parser(commonmark).parse('## Intro\n\n## Intro\n')
    first, second = root.children
    first.data = {'id': 'custom'}

    add_heading_ids(root)
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
