from __future__ import annotations

from wenmode_mkdocs import WenmodePlugin, markdown_to_html


def test_markdown_to_html_renders_github_markdown() -> None:
    html = markdown_to_html('# Title\n\n- [x] done\n\nA [link](/url).\n')

    assert '<h1 id="title">Title</h1>' in html
    assert '<input checked="" disabled="" type="checkbox"> done' in html
    assert '<a href="/url">link</a>' in html


def test_markdown_to_html_renders_colon_directives() -> None:
    html = markdown_to_html(':::note[Important]\nBody.\n:::\n')

    assert '<aside class="admonition admonition-note">' in html
    assert '<p class="admonition-title">Important</p>' in html
    assert '<p>Body.</p>' in html


def test_markdown_to_html_renders_fenced_directives() -> None:
    html = markdown_to_html('```{warning} Careful\n:class: extra\n\nBody.\n```\n')

    assert '<aside class="extra admonition admonition-warning">' in html
    assert '<p class="admonition-title">Careful</p>' in html
    assert '<p>Body.</p>' in html


def test_plugin_ignores_frontmatter_metadata_in_html() -> None:
    plugin = WenmodePlugin()

    html = plugin.on_page_markdown('---\ntitle: Example\nlayout: landing\n---\n\n# Example\n', None, None, None)

    assert 'layout: landing' not in html
    assert '<h1 id="example">Example</h1>' in html
