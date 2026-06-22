from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import configured_app
from wenmode import HTMLRenderer, MarkdownRenderer, RSTRenderer, Wenmode
from wenmode.directives import Admonition, Details, Figure, TableOfContents
from wenmode.nodes import Html, Image, Link, Literal, Paragraph, Parent, Root, Text
from wenmode.renderers import BaseRenderer, RenderContext
from wenmode.rules import (
    Footnote,
)

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
HTML_DIRECTIVES = {
    'admonition': Admonition,
    'details': Details,
    'figure': Figure,
    'toc': TableOfContents,
}
DEFAULT_HTML_DIRECTIVES = ['admonition', 'details', 'figure', 'toc']


@dataclass
class CustomLiteral(Literal):
    type: str = 'customLiteral'


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


def load_renderer_examples() -> list[RendererExample]:
    return load_fixture('renderer.json')


def html_directives_for_example(example: RendererExample):
    directive_names = example.get('html_directives', DEFAULT_HTML_DIRECTIVES)
    return [HTML_DIRECTIVES[name]() for name in directive_names]


def rule_names_for_example(example: RendererExample) -> list[str]:
    return example.get('rules', DEFAULT_RENDERER_RULES)


@pytest.mark.parametrize(
    'example',
    load_renderer_examples(),
    ids=lambda example: example['name'],
)
def test_renderer_examples(example: RendererExample) -> None:
    html_renderer = HTMLRenderer(
        directives=html_directives_for_example(example),
        **example.get('html_options', {}),
    )
    rule_names = rule_names_for_example(example)
    html_app = configured_app(rule_names, renderer=html_renderer)
    root = html_app.parse(example['input'])
    html = html_app.render_node(root)
    markdown = configured_app(rule_names, renderer=MarkdownRenderer()).render_node(root)
    rst = configured_app(rule_names, renderer=RSTRenderer()).render_node(root)

    if example.get('roundtrip_html'):
        assert configured_app(rule_names, renderer=html_renderer).render(markdown) == html

    assert html == example['html']
    assert markdown == example['markdown']
    assert rst == example['rst']


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


def test_html_renderer_sanitizes_obfuscated_unsafe_link_and_image_urls() -> None:
    node = Paragraph(
        children=[
            Link(url='java\nscript:alert(1)', children=[Text(value='bad')]),
            Text(value=' '),
            Image(url='vbscript:alert(1)', alt='"alt"'),
        ]
    )

    assert HTMLRenderer().render(node) == '<p><a>bad</a> <img alt="&quot;alt&quot;" /></p>\n'


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
