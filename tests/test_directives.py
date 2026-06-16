from __future__ import annotations

import json
from pathlib import Path
from typing import Any, NotRequired, TypedDict

import pytest

from wenmode import HTMLRenderer, MarkdownRenderer, Wenmode
from wenmode.directives import Admonition, Figure
from wenmode.rules import ContainerDirective, Emphasis, FencedCode, FencedDirective, LeafDirective, Role, TextDirective
from wenmode.rules import Image as ImageRule

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class DirectiveExample(TypedDict):
    name: str
    markdown: str
    ast: dict[str, Any]


class DirectiveHtmlExample(TypedDict):
    name: str
    markdown: str
    html: str
    admonition_types: NotRequired[list[str]]


def load_directive_examples() -> list[DirectiveExample]:
    return json.loads((FIXTURES_DIR / 'directives_ast.json').read_text())


def load_directive_html_examples() -> list[DirectiveHtmlExample]:
    return json.loads((FIXTURES_DIR / 'directives_html.json').read_text())


def render(parser: Wenmode, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


@pytest.mark.parametrize(
    'example',
    load_directive_examples(),
    ids=lambda example: example['name'],
)
def test_directive_ast_examples(example: DirectiveExample) -> None:
    parser = Wenmode([TextDirective, Role, LeafDirective, ContainerDirective, FencedDirective, Emphasis])

    assert parser.parse(example['markdown']).to_ast() == example['ast']


@pytest.mark.parametrize(
    'example',
    load_directive_html_examples(),
    ids=lambda example: example['name'],
)
def test_directive_html_examples(example: DirectiveHtmlExample) -> None:
    parser = Wenmode([ContainerDirective, TextDirective, ImageRule])
    admonition_types = example.get('admonition_types')
    admonition = Admonition(types=admonition_types) if admonition_types is not None else Admonition()

    assert HTMLRenderer(directives=[admonition, Figure()]).render(parser.parse(example['markdown'])) == example['html']


def test_directives_are_plain_text_without_rules() -> None:
    markdown = ':abbr[HTML]{title="HyperText Markup Language"}\n\n{abbr}`HTML`\n\n::youtube[Video]{#abc}\n'

    assert render(Wenmode([]), markdown) == (
        '<p>:abbr[HTML]{title=&quot;HyperText Markup Language&quot;}</p>\n'
        '<p>{abbr}`HTML`</p>\n'
        '<p>::youtube[Video]{#abc}</p>\n'
    )


def test_html_renderer_falls_back_to_directive_children() -> None:
    parser = Wenmode([TextDirective, LeafDirective, ContainerDirective])
    html = HTMLRenderer().render(parser.parse(':i[inline]\n\n::hr[leaf]\n\n:::note[Title]\nBody.\n:::\n'))

    assert html == '<p>inline</p>\nleaf<p>Title</p>\n<p>Body.</p>\n'


def test_markdown_renderer_outputs_directives() -> None:
    parser = Wenmode([TextDirective, Role, LeafDirective, ContainerDirective])
    markdown = ':i[inline]{.x} and {role}`text`\n\n::hr[leaf]{flag}\n\n:::note[Title]{#n}\nBody.\n:::\n'

    assert MarkdownRenderer().render(parser.parse(markdown)) == (
        ':i[inline]{.x} and :role[text]\n\n::hr[leaf]{flag}\n\n:::note[Title]{#n}\nBody\\.\n:::\n'
    )


def test_fenced_directive_serializes_as_container_directive() -> None:
    parser = Wenmode([FencedDirective])
    markdown = '```{note} Important\n:class: warning\n\nBody.\n```\n'

    assert MarkdownRenderer().render(parser.parse(markdown)) == ':::note[Important]{.warning}\nBody\\.\n:::\n'


def test_fenced_code_stays_code_when_not_directive() -> None:
    parser = Wenmode([FencedDirective, FencedCode])

    assert render(parser, '```py\nprint(1)\n```\n') == '<pre><code class="language-py">print(1)\n</code></pre>\n'


def test_fenced_directive_order_is_before_fenced_code() -> None:
    parser = Wenmode([FencedCode, FencedDirective])

    assert MarkdownRenderer().render(parser.parse('```{note} Important\nBody.\n```\n')) == (
        ':::note[Important]\nBody\\.\n:::\n'
    )
