from __future__ import annotations

from typing import Any

from wenmode import Wenmode
from wenmode.plugins import frontmatter


def test_frontmatter_plugin_stores_metadata_on_root_data() -> None:
    app = Wenmode().use(frontmatter)
    root = app.parse('---\ntitle: Hello\nlayout: "landing"\n# ignored\n---\n\n# Hi\n')

    assert root.data == {'frontmatter': {'title': 'Hello', 'layout': 'landing'}}
    assert app.render_node(root) == '<h1>Hi</h1>\n'


def test_frontmatter_plugin_preserves_child_source_positions() -> None:
    app = Wenmode(positions=True).use(frontmatter)
    root = app.parse('---\ntitle: Hello\n---\n\n# Hi\n')

    assert root.to_ast() == {
        'type': 'root',
        'data': {'frontmatter': {'title': 'Hello'}},
        'position': {
            'start': {'line': 1, 'column': 1, 'offset': 0},
            'end': {'line': 6, 'column': 1, 'offset': 27},
        },
        'children': [
            {
                'type': 'heading',
                'position': {
                    'start': {'line': 5, 'column': 1, 'offset': 22},
                    'end': {'line': 6, 'column': 1, 'offset': 27},
                },
                'children': [
                    {
                        'type': 'text',
                        'position': {
                            'start': {'line': 5, 'column': 3, 'offset': 24},
                            'end': {'line': 5, 'column': 5, 'offset': 26},
                        },
                        'value': 'Hi',
                    }
                ],
                'depth': 1,
            }
        ],
    }


def test_frontmatter_plugin_accepts_custom_parser_and_data_key() -> None:
    def parse_metadata(source: str) -> dict[str, Any]:
        return {'raw': source, 'lines': source.splitlines()}

    app = Wenmode().use(frontmatter, parser=parse_metadata, data_key='meta')
    root = app.parse('---\ntitle: Hello\n---\n\nBody\n')

    assert root.data == {'meta': {'raw': 'title: Hello\n', 'lines': ['title: Hello']}}


def test_frontmatter_plugin_does_not_change_unclosed_thematic_break() -> None:
    app = Wenmode().use(frontmatter)

    assert app.render('---\n') == '<hr />\n'


def test_frontmatter_plugin_only_consumes_top_level_fence() -> None:
    app = Wenmode().use(frontmatter)

    assert app.render('> ---\n> title: Hello\n> ---\n') == (
        '<blockquote>\n<hr />\n<h2>title: Hello</h2>\n</blockquote>\n'
    )
