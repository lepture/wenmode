from __future__ import annotations

from io import StringIO

import pytest

from wenmode import Wenmode
from wenmode.plugins import github_alert
from wenmode.renderers import AsciiDocRenderer, MarkdownRenderer, RSTRenderer
from wenmode.rules import Blockquote, Link


@pytest.mark.parametrize(
    ('name', 'title'),
    [
        ('NOTE', 'Note'),
        ('TIP', 'Tip'),
        ('IMPORTANT', 'Important'),
        ('WARNING', 'Warning'),
        ('CAUTION', 'Caution'),
    ],
)
def test_github_alert_renders_html(name: str, title: str) -> None:
    app = Wenmode(plugins=[github_alert])

    assert app.render(f'> [!{name}]\n> **Read** this.\n') == (
        f'<div class="markdown-alert markdown-alert-{name.lower()}">\n'
        f'<p class="markdown-alert-title">{title}</p>\n'
        '<p><strong>Read</strong> this.</p>\n'
        '</div>\n'
    )


def test_github_alert_can_render_admonition_html() -> None:
    app = Wenmode(plugins=[github_alert.configure(html_style='admonition')])

    assert app.render('> [!WARNING]\n> Body.\n') == (
        '<aside class="admonition admonition-warning">\n'
        '<p class="admonition-title">Warning</p>\n'
        '<p>Body.</p>\n'
        '</aside>\n'
    )


def test_github_alert_rejects_unknown_html_style() -> None:
    with pytest.raises(ValueError, match="html_style must be 'github' or 'admonition'"):
        github_alert.configure(html_style='plain')  # type: ignore[arg-type]


def test_github_alert_ast_shape() -> None:
    root = Wenmode(plugins=[github_alert]).parse('> [!note]\n> Body\n')

    assert root.to_ast()['children'] == [
        {
            'type': 'githubAlert',
            'children': [{'type': 'paragraph', 'children': [{'type': 'text', 'value': 'Body'}]}],
            'name': 'note',
        }
    ]


def test_github_alert_does_not_enable_blockquotes() -> None:
    app = Wenmode([], plugins=[github_alert])

    assert app.render('> [!NOTE]\n> Body\n') == '<p>&gt; [!NOTE]\n&gt; Body</p>\n'


def test_github_alert_leaves_unknown_markers_as_blockquotes() -> None:
    app = Wenmode([Blockquote], plugins=[github_alert])

    assert app.render('> [!DANGER]\n> Body\n') == '<blockquote>\n<p>[!DANGER]\nBody</p>\n</blockquote>\n'


def test_github_alert_is_top_level_only() -> None:
    app = Wenmode([Blockquote], plugins=[github_alert])

    assert app.render('> > [!NOTE]\n> > Body\n') == (
        '<blockquote>\n'
        '<blockquote>\n'
        '<p>[!NOTE]\nBody</p>\n'
        '</blockquote>\n'
        '</blockquote>\n'
    )


def test_github_alert_works_with_deferred_inlines() -> None:
    app = Wenmode([Blockquote, Link], plugins=[github_alert])

    assert app.render('> [!NOTE]\n> [Docs][docs]\n\n[docs]: https://example.com\n') == (
        '<div class="markdown-alert markdown-alert-note">\n'
        '<p class="markdown-alert-title">Note</p>\n'
        '<p><a href="https://example.com">Docs</a></p>\n'
        '</div>\n'
    )


def test_github_alert_streams() -> None:
    app = Wenmode([Blockquote], plugins=[github_alert])
    markdown = '> [!NOTE]\n> Body\n'

    assert ''.join(app.stream(markdown)) == app.render(markdown)
    assert ''.join(app.stream(StringIO(markdown))) == app.render(markdown)


def test_github_alert_does_not_duplicate_replacement() -> None:
    app = Wenmode([Blockquote], plugins=[github_alert])
    app.use(github_alert)

    assert type(app.parser.rules['blockquote']).__name__ == 'GithubAlertBlockquote'
    assert app.render('> [!NOTE]\n> Body\n').count('markdown-alert-note') == 1


def test_github_alert_renders_markdown() -> None:
    app = Wenmode(renderer=MarkdownRenderer(), plugins=[github_alert])

    assert app.render('> [!NOTE]\n> **Body**\n') == '> [!NOTE]\n> **Body**\n'


def test_github_alert_renders_empty_markdown() -> None:
    app = Wenmode(renderer=MarkdownRenderer(), plugins=[github_alert])

    assert app.render('> [!NOTE]\n') == '> [!NOTE]\n'


def test_github_alert_renders_rst() -> None:
    app = Wenmode(renderer=RSTRenderer(), plugins=[github_alert])

    assert app.render('> [!WARNING]\n> Body\n') == '.. warning::\n\n   Body\n'


def test_github_alert_renders_empty_rst() -> None:
    app = Wenmode(renderer=RSTRenderer(), plugins=[github_alert])

    assert app.render('> [!WARNING]\n') == '.. warning::\n'


def test_github_alert_renders_asciidoc() -> None:
    app = Wenmode(renderer=AsciiDocRenderer(), plugins=[github_alert])

    assert app.render('> [!TIP]\n> Body\n') == '[TIP]\n====\nBody\n====\n'


def test_github_alert_renders_empty_asciidoc() -> None:
    app = Wenmode(renderer=AsciiDocRenderer(), plugins=[github_alert])

    assert app.render('> [!TIP]\n') == '[TIP]\n====\n====\n'
