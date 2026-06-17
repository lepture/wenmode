from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

import pytest

from wenmode import HTMLRenderer, MarkdownRenderer, Parser
from wenmode.directives import Abbreviation, Admonition, Figure, TableOfContents
from wenmode.rules import (
    AtxHeading,
    ContainerDirective,
    Emphasis,
    FencedCode,
    FencedDirective,
    LeafDirective,
    Role,
    TextDirective,
)
from wenmode.rules import Image as ImageRule

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class DirectiveExample(TypedDict):
    name: str
    markdown: str
    ast: dict[str, Any]


class DirectiveHtmlExampleBase(TypedDict):
    name: str
    markdown: str
    html: str


class DirectiveHtmlExample(DirectiveHtmlExampleBase, total=False):
    admonition_names: list[str]


def load_directive_examples() -> list[DirectiveExample]:
    return json.loads((FIXTURES_DIR / 'directives_ast.json').read_text())


def load_directive_html_examples() -> list[DirectiveHtmlExample]:
    return json.loads((FIXTURES_DIR / 'directives_html.json').read_text())


def render(parser: Parser, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


@pytest.mark.parametrize(
    'example',
    load_directive_examples(),
    ids=lambda example: example['name'],
)
def test_directive_ast_examples(example: DirectiveExample) -> None:
    parser = Parser([TextDirective, Role, LeafDirective, ContainerDirective, FencedDirective, Emphasis])

    assert parser.parse(example['markdown']).to_ast() == example['ast']


@pytest.mark.parametrize(
    'example',
    load_directive_html_examples(),
    ids=lambda example: example['name'],
)
def test_directive_html_examples(example: DirectiveHtmlExample) -> None:
    parser = Parser([ContainerDirective, TextDirective, ImageRule])
    admonition_names = example.get('admonition_names')
    admonition = Admonition(names=admonition_names) if admonition_names is not None else Admonition()

    assert HTMLRenderer(directives=[admonition, Figure()]).render(parser.parse(example['markdown'])) == example['html']


def test_directives_are_plain_text_without_rules() -> None:
    markdown = ':abbr[HTML]{title="HyperText Markup Language"}\n\n{term}`HTML`\n\n::youtube[Video]{#abc}\n'

    assert render(Parser([]), markdown) == (
        '<p>:abbr[HTML]{title=&quot;HyperText Markup Language&quot;}</p>\n'
        '<p>{term}`HTML`</p>\n'
        '<p>::youtube[Video]{#abc}</p>\n'
    )


def test_html_renderer_falls_back_to_directive_children() -> None:
    parser = Parser([TextDirective, LeafDirective, ContainerDirective])
    html = HTMLRenderer().render(parser.parse(':i[inline]\n\n::hr[leaf]\n\n:::note[Title]\nBody.\n:::\n'))

    assert html == '<p>inline</p>\nleaf<p>Title</p>\n<p>Body.</p>\n'


def test_abbreviation_directive_renders_html() -> None:
    parser = Parser([TextDirective, Emphasis])
    root = parser.parse(':abbr[*HTML*]{title="HyperText Markup Language" .term}\n')

    assert HTMLRenderer(directives=[Abbreviation()]).render(root) == (
        '<p><abbr title="HyperText Markup Language" class="term"><em>HTML</em></abbr></p>\n'
    )


def test_abbreviation_directive_falls_back_without_title() -> None:
    parser = Parser([TextDirective, Role])
    root = parser.parse(':abbr[HTML]\n')

    assert HTMLRenderer(directives=[Abbreviation()]).render(root) == '<p>HTML</p>\n'


def test_markdown_renderer_outputs_directives() -> None:
    parser = Parser([TextDirective, Role, LeafDirective, ContainerDirective])
    markdown = ':i[inline]{.x} and {role}`text`\n\n::hr[leaf]{flag}\n\n:::note[Title]{#n}\nBody.\n:::\n'

    assert MarkdownRenderer().render(parser.parse(markdown)) == (
        ':i[inline]{.x} and :role[text]\n\n::hr[leaf]{flag}\n\n:::note[Title]{#n}\nBody\\.\n:::\n'
    )


def test_fenced_directive_serializes_as_container_directive() -> None:
    parser = Parser([FencedDirective])
    markdown = '```{note} Important\n:class: warning\n\nBody.\n```\n'

    assert MarkdownRenderer().render(parser.parse(markdown)) == ':::note[Important]{.warning}\nBody\\.\n:::\n'


def test_fenced_code_stays_code_when_not_directive() -> None:
    parser = Parser([FencedDirective, FencedCode])

    assert render(parser, '```py\nprint(1)\n```\n') == '<pre><code class="language-py">print(1)\n</code></pre>\n'


def test_fenced_directive_order_is_before_fenced_code() -> None:
    parser = Parser([FencedCode, FencedDirective])

    assert MarkdownRenderer().render(parser.parse('```{note} Important\nBody.\n```\n')) == (
        ':::note[Important]\nBody\\.\n:::\n'
    )


def test_toc_leaf_directive_renders_heading_links() -> None:
    parser = Parser([AtxHeading(id_transform=True), LeafDirective, ContainerDirective, Emphasis])
    root = parser.parse('::toc[On this page]{min=2 max=3 .wide}\n\n# Title\n\n## Usage *Guide*\n\n### Install\n\n## Usage Guide\n')

    assert HTMLRenderer(directives=[TableOfContents()]).render(root) == (
        '<nav class="wide toc" aria-label="On this page">\n'
        '<ol>\n'
        '<li><a href="#usage-guide">Usage Guide</a>\n'
        '<ol>\n'
        '<li><a href="#install">Install</a></li>\n'
        '</ol>\n'
        '</li>\n'
        '<li><a href="#usage-guide-1">Usage Guide</a></li>\n'
        '</ol>\n'
        '</nav>\n'
        '<h1 id="title">Title</h1>\n'
        '<h2 id="usage-guide">Usage <em>Guide</em></h2>\n'
        '<h3 id="install">Install</h3>\n'
        '<h2 id="usage-guide-1">Usage Guide</h2>\n'
    )


def test_toc_directive_uses_existing_heading_ids_even_when_rendered_late() -> None:
    parser = Parser([AtxHeading(id_transform=True), LeafDirective])
    root = parser.parse('## Before\n\n::toc{min-depth=2 max-depth=2 id=contents label=Contents}\n')

    assert HTMLRenderer(directives=[TableOfContents()]).render(root) == (
        '<h2 id="before">Before</h2>\n'
        '<nav id="contents" aria-label="Contents" class="toc">\n'
        '<ol>\n'
        '<li><a href="#before">Before</a></li>\n'
        '</ol>\n'
        '</nav>\n'
    )


def test_toc_directive_does_not_create_heading_ids() -> None:
    parser = Parser([AtxHeading, LeafDirective])
    root = parser.parse('## Before\n\n::toc{min=2 max=2}\n')

    assert HTMLRenderer(directives=[TableOfContents()]).render(root) == '<h2>Before</h2>\n'
