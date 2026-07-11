from __future__ import annotations

from typing import Any

import pytest

from wenmode import AsciiDocRenderer, MarkdownRenderer, RSTRenderer, StreamingUnsupportedError, Wenmode
from wenmode.plugins import frontmatter
from wenmode.presets import github, streaming


def test_frontmatter_plugin_stores_metadata_on_root_data() -> None:
    app = Wenmode().use(frontmatter)
    root = app.parse('---\ntitle: Hello\nlayout: "landing"\n# ignored\n---\n\n# Hi\n')

    assert root.data == {'frontmatter': {'title': 'Hello', 'layout': 'landing'}}
    assert app.render_node(root) == '<h1>Hi</h1>\n'


@pytest.mark.parametrize('renderer', [MarkdownRenderer(), RSTRenderer(), AsciiDocRenderer()])
def test_frontmatter_plugin_blocks_streaming_before_metadata_is_lost(renderer) -> None:
    app = Wenmode(streaming, renderer=renderer).use(frontmatter)
    stream = app.stream('---\ntitle: Hello\n---\n\n# Hi\n')

    assert app.supports_streaming is False
    assert app.parser.streaming_blockers() == ['frontmatter:frontmatter']
    assert app.renderer.streaming_blockers() == ['root:pre']
    assert app.streaming_blockers() == ['frontmatter:frontmatter', 'root:pre']
    with pytest.raises(StreamingUnsupportedError, match='frontmatter:frontmatter, root:pre'):
        next(stream)


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


def test_frontmatter_plugin_accepts_custom_load_and_data_key() -> None:
    def load_metadata(source: str) -> dict[str, Any]:
        return {'raw': source, 'lines': source.splitlines()}

    app = Wenmode().use(frontmatter.configure(load=load_metadata, data_key='meta'))
    root = app.parse('---\ntitle: Hello\n---\n\nBody\n')

    assert root.data == {'meta': {'raw': 'title: Hello\n', 'lines': ['title: Hello']}}


def test_frontmatter_default_load_skips_empty_keys() -> None:
    app = Wenmode().use(frontmatter)
    root = app.parse('---\n: ignored\n spaced : value\nplain\n---\n\nBody\n')

    assert root.data == {'frontmatter': {'spaced': 'value'}}


def test_frontmatter_plugin_does_not_change_unclosed_thematic_break() -> None:
    app = Wenmode().use(frontmatter)

    assert app.render('---\n') == '<hr />\n'


def test_frontmatter_plugin_only_consumes_top_level_fence() -> None:
    app = Wenmode().use(frontmatter)

    assert app.render('> ---\n> title: Hello\n> ---\n') == (
        '<blockquote>\n<hr />\n<h2>title: Hello</h2>\n</blockquote>\n'
    )


def test_frontmatter_plugin_renders_markdown_frontmatter() -> None:
    app = Wenmode(renderer=MarkdownRenderer()).use(frontmatter)

    assert app.render('---\ntitle: Hello\nlayout: "landing"\n---\n\n# Hi\n') == (
        '---\n'
        'title: Hello\n'
        'layout: landing\n'
        '---\n'
        '\n'
        '# Hi\n'
    )


def test_frontmatter_plugin_does_not_render_missing_frontmatter() -> None:
    markdown = Wenmode(renderer=MarkdownRenderer()).use(frontmatter)
    rst = Wenmode(renderer=RSTRenderer()).use(frontmatter)

    assert markdown.render('# Hi\n') == '# Hi\n'
    assert rst.render('# Hi\n') == 'Hi\n==\n'


def test_frontmatter_plugin_renders_empty_markdown_frontmatter() -> None:
    app = Wenmode(renderer=MarkdownRenderer()).use(frontmatter)

    assert app.render('---\n---\n\nBody\n') == '---\n---\n\nBody\n'


def test_frontmatter_plugin_skips_markdown_frontmatter_without_dump_output() -> None:
    app = Wenmode(renderer=MarkdownRenderer()).use(frontmatter.configure(load=lambda source: ['not', 'a', 'mapping']))

    assert app.render('---\ntitle: Hello\n---\n\n# Hi\n') == '# Hi\n'


def test_frontmatter_plugin_dumps_simple_scalar_values() -> None:
    def load_metadata(source: str) -> dict[str, object]:
        return {
            ' ': 'ignored',
            'draft': True,
            'published': False,
            'empty': None,
            'description': 'Line 1\nLine 2',
        }

    app = Wenmode(renderer=MarkdownRenderer()).use(frontmatter.configure(load=load_metadata))

    assert app.render('---\nignored: true\n---\n\nBody\n') == (
        '---\n'
        'draft: true\n'
        'published: false\n'
        'empty:\n'
        'description: Line 1 Line 2\n'
        '---\n'
        '\n'
        'Body\n'
    )


def test_frontmatter_plugin_renders_markdown_frontmatter_with_custom_dump() -> None:
    def load_metadata(source: str) -> dict[str, str]:
        return {'raw': source}

    def dump_metadata(value: Any) -> str | None:
        if not isinstance(value, dict):
            return None
        return value['raw']

    app = Wenmode(renderer=MarkdownRenderer()).use(
        frontmatter.configure(
            load=load_metadata,
            dump=dump_metadata,
            data_key='meta',
        )
    )

    assert app.render('---\ntitle: Hello\n---\n\nBody\n') == '---\ntitle: Hello\n---\n\nBody\n'


def test_frontmatter_plugin_renders_rst_docinfo() -> None:
    app = Wenmode(renderer=RSTRenderer()).use(frontmatter)

    assert app.render('---\ntitle: Hello\nlayout: "landing"\n---\n\n# Hi\n') == (
        ':title: Hello\n'
        ':layout: landing\n'
        '\n'
        'Hi\n'
        '==\n'
    )


def test_frontmatter_plugin_renders_asciidoc_attributes() -> None:
    app = Wenmode(renderer=AsciiDocRenderer()).use(frontmatter)

    assert app.render('---\ntitle: Hello\nlayout: "landing"\n---\n\n# Hi\n') == (
        ':title: Hello\n'
        ':layout: landing\n'
        '\n'
        '= Hi\n'
    )


def test_frontmatter_plugin_skips_rst_frontmatter_without_docinfo_fields() -> None:
    non_mapping = Wenmode(renderer=RSTRenderer()).use(frontmatter.configure(load=lambda source: ['not', 'a', 'mapping']))
    invalid_fields = Wenmode(renderer=RSTRenderer()).use(
        frontmatter.configure(load=lambda source: {'bad:name': 'value'})
    )

    assert non_mapping.render('---\ntitle: Hello\n---\n\n# Hi\n') == 'Hi\n==\n'
    assert invalid_fields.render('---\ntitle: Hello\n---\n\n# Hi\n') == 'Hi\n==\n'


def test_frontmatter_plugin_renders_rst_empty_docinfo_values() -> None:
    app = Wenmode(renderer=RSTRenderer()).use(
        frontmatter.configure(load=lambda source: {'bad:name': 'skip', ' ': 'skip', 'empty': None, 'ok': 'yes'})
    )

    assert app.render('---\ntitle: Hello\n---\n\n# Hi\n') == (
        ':empty:\n'
        ':ok: yes\n'
        '\n'
        'Hi\n'
        '==\n'
    )


def test_frontmatter_plugin_renders_before_markdown_footnotes() -> None:
    app = Wenmode(github, renderer=MarkdownRenderer()).use(frontmatter)

    assert app.render('---\ntitle: Hello\n---\n\nText[^a].\n\n[^a]: Note.\n') == (
        '---\n'
        'title: Hello\n'
        '---\n'
        '\n'
        'Text[^a]\\.\n'
        '\n'
        '[^a]: Note\\.\n'
    )


def test_frontmatter_plugin_renders_before_rst_footnotes() -> None:
    app = Wenmode(github, renderer=RSTRenderer()).use(frontmatter)

    assert app.render('---\ntitle: Hello\n---\n\nText[^a].\n\n[^a]: Note.\n') == (
        ':title: Hello\n'
        '\n'
        'Text[#a]_.\n'
        '\n'
        '.. [#a] Note.\n'
    )
