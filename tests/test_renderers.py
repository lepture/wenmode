from __future__ import annotations

from dataclasses import dataclass
from typing import Any, TypedDict, cast

import pytest

from tests.helpers import load_text_fixture, parse_text_fixture
from tests.plugin_helpers import configured_app
from wenmode import AsciiDocRenderer, HTMLRenderer, MarkdownRenderer, RSTRenderer, StreamingUnsupportedError, Wenmode
from wenmode.ast import from_ast
from wenmode.directives import Admonition, Details, Figure, TableOfContents
from wenmode.nodes import Html, Image, Link, List, ListItem, Literal, Paragraph, Parent, Root, Text
from wenmode.plugins import fenced_directive, html_container, inline_math
from wenmode.presets import github, streaming
from wenmode.renderers import BaseRenderer, RenderContext
from wenmode.rules import Footnote

DEFAULT_RENDERER_RULES = [
    'abbreviation',
    'table',
    'thematic_break',
    'fenced_directive',
    'container_directive',
    'leaf_directive',
    'fenced_code',
    'indented_code',
    'html_block',
    'task_list',
    'atx_heading',
    'setext_heading',
    'blockquote',
    'block_spoiler',
    'definition_list',
    'footnote',
    'math_block',
    'hard_break',
    'autolink',
    'raw_html',
    'backslash_escape',
    'character_reference',
    'image',
    'link',
    'inline_code',
    'inline_math',
    'inline_spoiler',
    'text_directive',
    'role',
    'strikethrough',
    'emphasis',
    'mark',
    'insert',
    'superscript',
    'subscript',
    'ruby',
    'extended_autolink',
]
HTML_DIRECTIVES = {'admonition': Admonition, 'details': Details, 'figure': Figure, 'toc': TableOfContents}
DEFAULT_HTML_DIRECTIVES = ['admonition', 'details', 'figure', 'toc']


@dataclass
class CustomLiteral(Literal):
    type: str = 'customLiteral'


def test_restored_html_cannot_assert_internal_escaping_by_default() -> None:
    with pytest.raises(ValueError, match='^AST html "data.escaped" is internal metadata'):
        from_ast({'type': 'html', 'value': '<em>safe</em>', 'data': {'escaped': True}})


def test_restored_html_preserves_internal_escaping_for_trusted_ast() -> None:
    node = from_ast(
        {'type': 'html', 'value': '&lt;em&gt;safe&lt;/em&gt;', 'data': {'escaped': True}}, allow_internal_metadata=True
    )

    assert HTMLRenderer().render(node) == '&lt;em&gt;safe&lt;/em&gt;'


def test_restored_html_container_preserves_internal_escaping_for_trusted_ast() -> None:
    ast = {
        'type': 'htmlContainer',
        'data': {'escaped': True},
        'children': [],
        'name': 'div',
        'opening': '&lt;div&gt;',
        'closing': '&lt;/div&gt;',
    }
    node = from_ast(ast, nodes=html_container.nodes, allow_internal_metadata=True)

    assert node.to_ast() == ast
    assert configured_app(['html_container']).render_node(node) == '&lt;div&gt;\n&lt;/div&gt;\n'


def test_generic_html_container_cannot_assert_escaping_before_plugin_rendering() -> None:
    with pytest.raises(ValueError, match='^AST htmlContainer "data.escaped" is internal metadata'):
        node = from_ast(
            {
                'type': 'htmlContainer',
                'data': {'escaped': True},
                'children': [],
                'opening': '<script>',
                'closing': '</script>',
            }
        )
        configured_app(['html_container']).render_node(node)


@dataclass
class CustomParent(Parent):
    type: str = 'customParent'


@dataclass
class CustomElement(Parent):
    type: str = 'customElement'


class CustomRenderer(BaseRenderer):
    pass


class RendererExample(TypedDict, total=False):
    name: str
    input: str
    rules: list[str]
    html_options: dict[str, bool]
    html_directives: list[str]
    roundtrip_html: bool
    html: str
    markdown: str
    rst: str
    asciidoc: str


def load_renderer_examples() -> list[RendererExample]:
    return load_text_fixture('renderer.md')


def test_text_fixture_parser_rejects_unclosed_case() -> None:
    text = '## broken\n\n````````fixture\n.input\nx\n'

    with pytest.raises(ValueError, match='missing a closing fence'):
        parse_text_fixture(text)


def test_text_fixture_parser_rejects_case_closed_after_next_case_start() -> None:
    text = '## first\n\n````````fixture\n.input\nx\n````\n\n## second\n\n````````fixture\n.input\ny\n````````\n'

    with pytest.raises(ValueError, match="missing a closing fence before 'second'"):
        parse_text_fixture(text)


def test_text_fixture_parser_rejects_duplicate_sections() -> None:
    text = '## broken\n\n````````fixture\n.input\nx\n.input\ny\n````````\n'

    with pytest.raises(ValueError, match="section 'input' more than once"):
        parse_text_fixture(text)


def test_text_fixture_parser_unescapes_literal_section_markers() -> None:
    text = '## escaped\n\n````````fixture\n.input\n\\.html\n\\.rst\n.html\n<p>.html</p>\n````````\n'

    assert parse_text_fixture(text) == [{'name': 'escaped', 'input': '.html\n.rst', 'html': '<p>.html</p>'}]


def html_directives_for_example(example: RendererExample):
    directive_names = example.get('html_directives', DEFAULT_HTML_DIRECTIVES)
    return [HTML_DIRECTIVES[name]() for name in directive_names]


def rule_names_for_example(example: RendererExample) -> list[str]:
    return example.get('rules', DEFAULT_RENDERER_RULES)


@pytest.mark.parametrize('example', load_renderer_examples(), ids=lambda example: example['name'])
def test_renderer_examples(example: RendererExample) -> None:
    html_renderer = HTMLRenderer(directives=html_directives_for_example(example), **example.get('html_options', {}))
    rule_names = rule_names_for_example(example)
    html_app = configured_app(rule_names, renderer=html_renderer)
    root = html_app.parse(example['input'])
    html = html_app.render_node(root)
    markdown = configured_app(rule_names, renderer=MarkdownRenderer()).render_node(root)
    rst = configured_app(rule_names, renderer=RSTRenderer()).render_node(root)
    asciidoc = configured_app(rule_names, renderer=AsciiDocRenderer()).render_node(root)

    if example.get('roundtrip_html'):
        assert configured_app(rule_names, renderer=html_renderer).render(markdown) == html

    assert html == example['html']
    assert markdown == example['markdown']
    assert rst == example['rst']
    if 'asciidoc' in example:
        assert asciidoc == example['asciidoc']


def test_asciidoc_renderer_renders_empty_blockquote_from_markdown() -> None:
    app = Wenmode(github, renderer=AsciiDocRenderer())

    assert app.render('>\n') == '____\n____\n'


def test_asciidoc_renderer_renders_empty_code_block_from_markdown() -> None:
    app = Wenmode(github, renderer=AsciiDocRenderer())

    assert app.render('```\n```\n') == '----\n----\n'


def test_asciidoc_renderer_renders_html_block_from_markdown() -> None:
    app = Wenmode(github, renderer=AsciiDocRenderer())

    assert app.render('<div>\nx\n</div>\n') == '++++\n<div>\nx\n</div>\n++++\n'


def test_asciidoc_renderer_renders_image_title_from_markdown() -> None:
    app = Wenmode(github, renderer=AsciiDocRenderer())

    assert app.render('![Alt](/img "A title")\n') == 'image:/img[Alt,title="A title"]\n'


def test_asciidoc_renderer_renders_inline_code_with_plus_from_markdown() -> None:
    app = Wenmode(github, renderer=AsciiDocRenderer())

    assert app.render('`a+b`\n') == '++a+b++\n'


def test_markdown_renderer_renders_directive_flag_attribute_from_markdown() -> None:
    app = Wenmode(github, renderer=MarkdownRenderer(), plugins=[fenced_directive])

    assert app.render('```{note}\n:flag:\n```\n') == ':::note{flag}\n:::\n'


def test_markdown_renderer_renders_wrapped_link_destination_from_markdown() -> None:
    app = Wenmode(github, renderer=MarkdownRenderer())

    assert app.render('[x](<a b> "ti\\"tle")\n') == '[x](a%20b "ti\\"tle")\n'


def test_renderer_registers_custom_node_handler() -> None:
    @CustomRenderer.register('customLiteral')
    def render_custom_literal(renderer: CustomRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<custom>{node.value}</custom>'

    assert CustomRenderer().render(CustomLiteral(value='<x>')) == '<custom><x></custom>'


def test_renderer_root_hooks_wrap_root_rendering() -> None:
    renderer = CustomRenderer()

    renderer.register_handler('root:pre', lambda renderer, node, context: 'before:')
    renderer.register_handler('root:post', lambda renderer, node, context: ':after')

    assert renderer.render(Root(children=[Text(value='body')])) == 'before:body:after'


def test_renderer_class_root_hooks_wrap_root_rendering() -> None:
    class LocalRenderer(BaseRenderer):
        pass

    @LocalRenderer.register('root:pre')
    def render_before(renderer: LocalRenderer, node: Root, context: RenderContext) -> str:
        return 'before:'

    @LocalRenderer.register('root:post')
    def render_after(renderer: LocalRenderer, node: Root, context: RenderContext) -> str:
        return ':after'

    assert LocalRenderer().render(Root(children=[Text(value='body')])) == 'before:body:after'


def test_renderer_class_root_hooks_block_streaming_by_default() -> None:
    class LocalRenderer(BaseRenderer):
        pass

    @LocalRenderer.register('root:post')
    def render_after(renderer: LocalRenderer, node: Root, context: RenderContext) -> str:
        return ':after'

    renderer = LocalRenderer()
    app = Wenmode(streaming, renderer=renderer)

    assert renderer.supports_streaming is False
    assert renderer.streaming_blockers() == ['root:post']
    assert app.supports_streaming is False
    assert app.streaming_blockers() == ['root:post']
    with pytest.raises(StreamingUnsupportedError, match='root:post'):
        next(app.stream('Body\n'))


@pytest.mark.parametrize('hook_name', ['root:pre', 'root:post'])
def test_renderer_dynamic_root_hooks_block_streaming(hook_name: str) -> None:
    renderer = HTMLRenderer()
    renderer.register_handler(hook_name, lambda renderer, node, context: '')
    app = Wenmode(streaming, renderer=renderer)

    assert renderer.supports_streaming is False
    assert renderer.streaming_blockers() == [hook_name]
    assert app.supports_streaming is False
    assert app.streaming_blockers() == [hook_name]
    with pytest.raises(StreamingUnsupportedError, match=hook_name):
        next(app.stream('Body\n'))


def test_html_root_post_hook_is_safe_to_omit_during_supported_streaming() -> None:
    app = Wenmode(streaming, renderer=HTMLRenderer())
    markdown = '# Title\n\nBody with ![alt](/img.png).\n'

    assert app.renderer.streaming_blockers() == []
    assert app.supports_streaming is True
    assert ''.join(app.stream(markdown)) == app.render(markdown)


def test_rst_root_post_hook_is_safe_to_omit_for_direct_streaming_images() -> None:
    app = Wenmode(streaming, renderer=RSTRenderer())

    assert app.renderer.streaming_blockers() == []
    assert app.supports_streaming is True
    assert ''.join(app.stream('![alt](https://example.com/img.png "title")\n')) == (
        '.. image:: https://example.com/img.png\n   :alt: alt\n   :title: title\n\n\n\n'
    )


def test_base_renderer_unknown_nodes_fall_back_to_children_or_value() -> None:
    renderer = BaseRenderer()

    assert renderer.render(CustomParent(children=[CustomLiteral(value='a'), CustomLiteral(value='b')])) == 'ab'
    assert renderer.render(CustomLiteral(value='literal')) == 'literal'


def test_html_renderer_custom_elements_require_registered_handler() -> None:
    node = Paragraph(children=[CustomElement(children=[Text(value='marked')])])
    renderer = HTMLRenderer()

    assert renderer.render(node) == '<p>marked</p>\n'

    def render_custom_element(renderer: HTMLRenderer, node: CustomElement, context: RenderContext) -> str:
        attrs = renderer.render_attrs({'data-custom': 'yes', 'hidden': False})
        return f'<mark{attrs}>{renderer.render_children(node.children, context)}</mark>'

    renderer.register_handler('customElement', render_custom_element)

    assert renderer.render(node) == '<p><mark data-custom="yes">marked</mark></p>\n'


def test_html_renderer_escapes_unknown_literal_nodes_without_registered_handler() -> None:
    literal = CustomLiteral(value='<mark title="unsafe">&</mark>')

    assert HTMLRenderer().render(literal) == '&lt;mark title=&quot;unsafe&quot;&gt;&amp;&lt;/mark&gt;'
    assert HTMLRenderer().render(CustomParent(children=[literal])) == (
        '&lt;mark title=&quot;unsafe&quot;&gt;&amp;&lt;/mark&gt;'
    )

    raw_renderer = HTMLRenderer(escape=False)
    assert raw_renderer.render(literal) == '&lt;mark title=&quot;unsafe&quot;&gt;&amp;&lt;/mark&gt;'
    assert raw_renderer.render(Html(value='<mark>trusted</mark>')) == '<mark>trusted</mark>'

    def render_custom_literal(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<mark>{renderer.escape_html(node.value)}</mark>'

    raw_renderer.register_handler('customLiteral', render_custom_literal)

    assert raw_renderer.render(literal) == '<mark>&lt;mark title=&quot;unsafe&quot;&gt;&amp;&lt;/mark&gt;</mark>'


def test_html_renderer_escapes_attribute_values_and_drops_unsafe_names() -> None:
    renderer = HTMLRenderer()

    attrs = renderer.render_attrs(
        {
            'title': '"<x>&',
            'onclick': 'alert(1)',
            'style': 'position:fixed',
            'bad name': 'bad',
            'hidden': True,
            'disabled': False,
            'empty': None,
            'data-count': 3,
        }
    )

    assert attrs == ' title="&quot;&lt;x&gt;&amp;" hidden data-count="3"'


def test_html_renderer_escapes_ordered_list_start_attribute() -> None:
    node = List(
        ordered=True,
        start=cast(Any, '2" data-sentinel="safe'),
        spread=False,
        children=[ListItem(children=[Paragraph(children=[Text(value='item')])])],
    )

    assert HTMLRenderer().render(node) == '<ol start="2&quot; data-sentinel=&quot;safe">\n<li>item</li>\n</ol>\n'


@pytest.mark.parametrize(
    ('start', 'expected'),
    [
        (1, '<ol>\n</ol>\n'),
        (2, '<ol start="2">\n</ol>\n'),
        (0, '<ol start="0">\n</ol>\n'),
        (-1, '<ol start="-1">\n</ol>\n'),
    ],
)
def test_html_renderer_preserves_ordered_list_start_output(start: int, expected: str) -> None:
    node = List(ordered=True, start=start, spread=False, children=[])

    assert HTMLRenderer().render(node) == expected


def test_html_renderer_sanitizes_obfuscated_unsafe_link_and_image_urls() -> None:
    node = Paragraph(
        children=[
            Link(url='java\nscript:alert(1)', children=[Text(value='bad')]),
            Text(value=' '),
            Image(url='vbscript:alert(1)', alt='"alt"'),
        ]
    )

    assert HTMLRenderer().render(node) == '<p><a>bad</a> <img alt="&quot;alt&quot;" /></p>\n'


def test_html_renderer_sanitizes_percent_encoded_unsafe_urls() -> None:
    node = Paragraph(
        children=[
            Link(url='javascript%3Aalert(1)', children=[Text(value='bad')]),
            Text(value=' '),
            Link(url='%6aavascript:alert(1)', children=[Text(value='bad')]),
            Text(value=' '),
            Link(url='java%0ascript:alert(1)', children=[Text(value='bad')]),
            Text(value=' '),
            Image(url='javascript%253Aalert(1)', alt='bad'),
        ]
    )

    assert HTMLRenderer().render(node) == '<p><a>bad</a> <a>bad</a> <a>bad</a> <img alt="bad" /></p>\n'


def test_html_renderer_keeps_safe_percent_encoded_urls() -> None:
    node = Paragraph(
        children=[
            Link(url='https://example.com/%6aavascript%3Aalert(1)', children=[Text(value='safe')]),
            Text(value=' '),
            Link(url='mailto:user%2Btag@example.com', children=[Text(value='mail')]),
            Text(value=' '),
            Link(url='/docs/foo%3Abar', children=[Text(value='relative')]),
        ]
    )

    assert HTMLRenderer().render(node) == (
        '<p><a href="https://example.com/%6aavascript%3Aalert(1)">safe</a> '
        '<a href="mailto:user%2Btag@example.com">mail</a> '
        '<a href="/docs/foo%3Abar">relative</a></p>\n'
    )


def test_html_renderer_can_disable_url_sanitization_for_trusted_content() -> None:
    node = Paragraph(
        children=[
            Link(url='javascript:alert(1)', children=[Text(value='bad')]),
            Text(value=' '),
            Image(url='javascript:alert(2)', alt='bad'),
        ]
    )

    assert HTMLRenderer(sanitize_urls=False).render(node) == (
        '<p><a href="javascript:alert(1)">bad</a> <img src="javascript:alert(2)" alt="bad" /></p>\n'
    )


def test_html_renderer_escapes_raw_html_by_default_and_can_pass_it_through() -> None:
    node = Html(value='<script>alert("x")</script>')

    assert HTMLRenderer().render(node) == '&lt;script&gt;alert(&quot;x&quot;)&lt;/script&gt;'
    assert HTMLRenderer(escape=False).render(node) == '<script>alert("x")</script>'


def test_html_renderer_reuses_instance_without_leaking_footnote_state() -> None:
    app = Wenmode([Footnote])
    renderer = HTMLRenderer()
    root = app.parse('a[^one]\n\n[^one]: note\n')

    first = renderer.render(root)
    second = renderer.render(root)

    assert second == first
    assert 'id="user-content-fnref-one-2"' not in second


def test_rst_renderer_keeps_backticks_inside_inline_code_valid() -> None:
    app = configured_app(['inline_code'], renderer=RSTRenderer())

    assert app.render('```` ```{name} ````\n') == ':literal:`\\`\\`\\`{name}`\n'


def test_rst_renderer_uses_plain_text_for_link_labels() -> None:
    app = configured_app(['link', 'inline_code'], renderer=RSTRenderer())

    assert app.render('[`mdast-util-directive`](https://example.com)\n') == (
        '`mdast-util-directive <https://example.com>`__\n'
    )


def test_rst_renderer_normalizes_multiline_image_options() -> None:
    app = Wenmode(renderer=RSTRenderer())

    assert app.render('![line1\nline2](https://example.com/img.png "title1\ntitle2")\n') == (
        '|image-1|\n'
        '\n'
        '.. |image-1| image:: https://example.com/img.png\n'
        '   :alt: line1 line2\n'
        '   :title: title1 title2\n'
    )


def test_rst_renderer_escapes_backticks_in_inline_math() -> None:
    app = Wenmode(renderer=RSTRenderer(), plugins=[inline_math])

    assert app.render('$x` y$\n') == ':math:`x\\` y`\n'


@pytest.mark.parametrize(
    'markdown',
    [
        '- item\n  - sub\n',
        '- item\n  continued\n  - sub\n',
        '- [ ] task\n  - [x] subtask\n',
        '- [ ] task\n  continued\n  - [x] subtask\n',
    ],
)
def test_markdown_renderer_round_trips_nested_lists(markdown: str) -> None:
    html_app = configured_app(['task_list'])
    markdown_app = configured_app(['task_list'], renderer=MarkdownRenderer())

    reformatted = markdown_app.render(markdown)

    assert html_app.render(reformatted) == html_app.render(markdown)
