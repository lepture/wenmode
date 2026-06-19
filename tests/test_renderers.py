from __future__ import annotations

from dataclasses import dataclass
from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import configured_app
from wenmode import HTMLRenderer, MarkdownRenderer, RSTRenderer, Wenmode
from wenmode.directives import Admonition, Details, Figure, TableOfContents
from wenmode.nodes import Literal, Paragraph, Parent, Text
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


def test_html_renderer_reuses_instance_without_leaking_footnote_state() -> None:
    app = Wenmode([Footnote])
    renderer = HTMLRenderer()
    root = app.parse('a[^one]\n\n[^one]: note\n')

    first = renderer.render(root)
    second = renderer.render(root)

    assert second == first
    assert 'id="user-content-fnref-one-2"' not in second
