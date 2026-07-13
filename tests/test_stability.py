from __future__ import annotations

from io import StringIO
from pathlib import Path

import pytest

from wenmode import StreamingUnsupportedError, Wenmode
from wenmode.plugins import (
    BlockFenced,
    InlineDelimited,
    InlineLiteral,
    PluginModule,
    RendererHandlers,
    abbr,
    block_math,
    block_spoiler,
    heading_ids,
    inline_math,
    inline_spoiler,
)
from wenmode.presets import github, streaming
from wenmode.rules import Footnote, Link

ROOT = Path(__file__).resolve().parents[1]
PRIVATE_IMPORT_MARKERS = ('from wenmode._', 'import wenmode._')


def test_positions_survive_plugin_root_transforms() -> None:
    app = Wenmode(positions=True).use(abbr)
    root = app.parse('*[HTML]: HyperText\n\nHTML and HTML\n')

    paragraph = root.to_ast()['children'][0]
    first, middle, second = paragraph['children']

    assert first == {
        'type': 'abbreviation',
        'position': {'start': {'line': 3, 'column': 1, 'offset': 20}, 'end': {'line': 3, 'column': 5, 'offset': 24}},
        'children': [
            {
                'type': 'text',
                'position': {
                    'start': {'line': 3, 'column': 1, 'offset': 20},
                    'end': {'line': 3, 'column': 5, 'offset': 24},
                },
                'value': 'HTML',
            }
        ],
        'title': 'HyperText',
    }
    assert middle == {
        'type': 'text',
        'position': {'start': {'line': 3, 'column': 5, 'offset': 24}, 'end': {'line': 3, 'column': 10, 'offset': 29}},
        'value': ' and ',
    }
    assert second['position'] == {
        'start': {'line': 3, 'column': 10, 'offset': 29},
        'end': {'line': 3, 'column': 14, 'offset': 33},
    }


def test_plugin_state_is_created_per_parse() -> None:
    app = Wenmode().use(abbr)

    assert app.render('*[HTML]: HyperText\n\nHTML\n') == '<p><abbr title="HyperText">HTML</abbr></p>\n'
    assert app.render('HTML\n') == '<p>HTML</p>\n'


def test_streaming_preset_supports_streaming_compatible_plugins() -> None:
    app = Wenmode(streaming).use(block_math).use(inline_math).use(block_spoiler).use(inline_spoiler)
    markdown = 'A $x$ and >! hidden !<.\n\n- [x] done\n'

    assert ''.join(app.stream(markdown)) == app.render(markdown)
    assert ''.join(app.stream(StringIO(markdown))) == app.render(markdown)


def test_streaming_rejects_plugins_with_deferred_transforms() -> None:
    with pytest.raises(StreamingUnsupportedError, match='deferred inline transforms'):
        next(Wenmode(streaming).use(abbr).stream('HTML\n\n*[HTML]: HyperText\n'))


@pytest.mark.parametrize('rule', [Link, Footnote])
def test_streaming_rejects_core_rules_with_deferred_transforms(rule) -> None:
    with pytest.raises(StreamingUnsupportedError, match='deferred inline transforms'):
        next(Wenmode([rule]).stream('text\n'))


def test_documented_public_extension_imports_resolve() -> None:
    import wenmode
    import wenmode.plugins
    import wenmode.renderers
    from wenmode import HTMLRenderer, MarkdownRenderer, Parser, RSTRenderer
    from wenmode.ast import find_all, from_ast, plain_text, walk
    from wenmode.nodes import BUILTIN_NODES, LiteralDirective, Root, Text
    from wenmode.renderers import BaseRenderer, DirectiveHtmlRenderer, RenderContext, RenderHandler
    from wenmode.rules import BlockRule, ContinueRule, InlineRule, Rule
    from wenmode.state import BlockState, SourceMap, StateKey, StateStore

    assert wenmode.HTMLRenderer is HTMLRenderer
    assert wenmode.MarkdownRenderer is MarkdownRenderer
    assert wenmode.RSTRenderer is RSTRenderer
    assert wenmode.Parser is Parser
    assert all(name not in wenmode.__all__ for name in {'Plugin', 'PluginConfig', 'PluginTarget'})
    assert all(name not in wenmode.plugins.__all__ for name in {'Plugin', 'PluginConfig', 'PluginTarget'})
    assert {'BlockFenced', 'InlineDelimited', 'InlineLiteral', 'PluginModule', 'RendererHandlers'}.issubset(
        wenmode.plugins.__all__
    )
    assert all('_parser' not in name for name in wenmode.__all__)
    assert all(
        name not in wenmode.renderers.__all__
        for name in {'delimiter_for_align', 'normalize_table_row', 'quote_directive_attribute'}
    )
    assert {
        'AsciiDocRenderer',
        'BaseRenderer',
        'DirectiveHtmlRenderer',
        'HTMLRenderer',
        'MarkdownRenderer',
        'RSTRenderer',
        'RenderContext',
        'RenderHandler',
        'render_node_children',
    }.issubset(wenmode.renderers.__all__)
    assert {node.type: node for node in BUILTIN_NODES}['literalDirective'] is LiteralDirective
    assert isinstance(from_ast({'type': 'literalDirective', 'name': 'code-block', 'value': 'x'}), LiteralDirective)
    assert plain_text(Root(children=[Text(value='text')])) == 'text'
    assert list(find_all(Root(children=[Text(value='text')]), Text))
    assert [node.type for node in walk(Root(children=[Text(value='text')]))] == ['root', 'text']
    assert BaseRenderer and DirectiveHtmlRenderer and RenderContext and RenderHandler
    assert BlockRule and ContinueRule and InlineRule and Rule
    assert BlockState and SourceMap and StateKey and StateStore
    assert BlockFenced and InlineDelimited and InlineLiteral
    assert PluginModule and RendererHandlers
    assert heading_ids


def test_public_state_facade_reexports_private_implementations() -> None:
    import wenmode.state as state
    from wenmode._parser.source import (
        NULL_SOURCE_COLLECTOR,
        LineSource,
        NullSourceCollector,
        NullSourceTracker,
        PositionSourceCollector,
            PositionSourceTracker,
            SourceCollector,
            SourceMap,
            SourceSegment,
            StreamPositionSourceTracker,
        )
    from wenmode._parser.state import BlockState, StreamBlockState, StreamLineBuffer
    from wenmode._parser.store import StateKey, StateStore

    expected = {
        'NULL_SOURCE_COLLECTOR': NULL_SOURCE_COLLECTOR,
        'BlockState': BlockState,
        'LineSource': LineSource,
        'NullSourceCollector': NullSourceCollector,
        'NullSourceTracker': NullSourceTracker,
        'PositionSourceCollector': PositionSourceCollector,
        'PositionSourceTracker': PositionSourceTracker,
        'SourceCollector': SourceCollector,
        'SourceMap': SourceMap,
        'SourceSegment': SourceSegment,
        'StreamPositionSourceTracker': StreamPositionSourceTracker,
        'StateKey': StateKey,
        'StateStore': StateStore,
        'StreamBlockState': StreamBlockState,
        'StreamLineBuffer': StreamLineBuffer,
    }

    assert state.__all__ == list(expected)
    assert all(getattr(state, name) is implementation for name, implementation in expected.items())
    assert all('_parser' not in name for name in state.__all__)


def test_public_docs_and_examples_do_not_import_private_parser_modules() -> None:
    paths = [
        ROOT / 'README.md',
        *sorted(path for path in (ROOT / 'docs').rglob('*') if path.suffix in {'.md', '.rst'}),
        *sorted(path for path in (ROOT / 'examples').rglob('*') if path.suffix in {'.md', '.rst', '.py'}),
    ]
    offenders = []
    for path in paths:
        text = path.read_text(encoding='utf-8')
        if any(marker in text for marker in PRIVATE_IMPORT_MARKERS):
            offenders.append(str(path.relative_to(ROOT)))

    assert offenders == []


def test_default_html_policy_escapes_raw_html_and_sanitizes_urls_after_parse() -> None:
    html = Wenmode().render('<script>alert(1)</script>\n\n[x](javascript:alert(1)) ![a](javascript:img)\n')

    assert html == '&lt;script&gt;alert(1)&lt;/script&gt;\n<p><a>x</a> <img alt="a" /></p>\n'


def test_github_nested_disallowed_html_is_escaped_once() -> None:
    html = Wenmode(github).render('<div>\n<script>alert(1)</script>\n</div>\n')

    assert '<script>' not in html
    assert '</script>' not in html
    assert '&lt;script>alert(1)&lt;/script>' in html
    assert '&amp;lt;script' not in html


def test_streaming_positions_remain_offset_only_for_plugin_nodes() -> None:
    parser = (
        Wenmode(streaming, positions=True)
        .use(block_math)
        .use(inline_math)
        .use(block_spoiler)
        .use(inline_spoiler)
        .parser
    )
    markdown = 'A $x$ and >! hidden !<.\n'

    paragraph = next(parser.parse_iter(markdown)).to_ast()

    assert paragraph['position'] == {'start': {'offset': 0}, 'end': {'offset': 24}}
    assert paragraph['children'][1] == {
        'type': 'inlineMath',
        'position': {'start': {'offset': 2}, 'end': {'offset': 5}},
        'value': 'x',
    }
    assert paragraph['children'][3] == {
        'type': 'inlineSpoiler',
        'position': {'start': {'offset': 10}, 'end': {'offset': 22}},
        'children': [{'type': 'text', 'position': {'start': {'offset': 13}, 'end': {'offset': 19}}, 'value': 'hidden'}],
    }
