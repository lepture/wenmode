from __future__ import annotations

import pytest

from wenmode import MarkdownRenderer, Wenmode
from wenmode.nodes import Node, TableCell, TableRow, Text
from wenmode.presets import commonmark
from wenmode.renderers import RenderContext, delimiter_for_align, normalize_table_row, quote_directive_attribute
from wenmode.rules import Footnote, MathBlock
from wenmode.rules import InlineMath as InlineMathRule

from ._renderer_fixtures import RendererExample, load_renderer_examples, node_from_renderer_example


@pytest.mark.parametrize(
    'example',
    load_renderer_examples('markdown_render.json'),
    ids=lambda example: example['name'],
)
def test_markdown_renderer_examples(example: RendererExample) -> None:
    assert MarkdownRenderer().render(node_from_renderer_example(example)) == example['output']


def test_markdown_renderer_round_trips_to_equivalent_html() -> None:
    html_app = Wenmode(commonmark)
    markdown_app = Wenmode(commonmark, renderer=MarkdownRenderer())
    markdown = '# A\n\n> hi *there*\n\n- one\n- two\n\n```py\nprint(1)\n```\n\n[link](/url "t") and ![alt](/img.png)\n'

    html = html_app.render(markdown)
    rendered_markdown = markdown_app.render(markdown)

    assert html_app.render(rendered_markdown) == html


def test_markdown_renderer_round_trips_footnotes_to_equivalent_html() -> None:
    html_app = Wenmode([Footnote])
    markdown_app = Wenmode([Footnote], renderer=MarkdownRenderer())
    markdown = 'a[^one]\n\n[^one]: first\n  \n  second\n'

    html = html_app.render(markdown)
    rendered_markdown = markdown_app.render(markdown)

    assert html_app.render(rendered_markdown) == html


def test_markdown_renderer_round_trips_math_to_equivalent_html() -> None:
    rules = [MathBlock, InlineMathRule]
    html_app = Wenmode(rules)
    markdown_app = Wenmode(rules, renderer=MarkdownRenderer())
    markdown = 'inline $x < y$\n\n$$\na & b\n$$\n'

    html = html_app.render(markdown)
    rendered_markdown = markdown_app.render(markdown)

    assert html_app.render(rendered_markdown) == html


def test_markdown_renderer_helper_edges() -> None:
    renderer = MarkdownRenderer()

    assert renderer.render_directive_label(Node(type='bare'), RenderContext()) == ''
    assert renderer.render_directive_attributes({'id': '', 'class': '  ', 'empty': ''}) == '{empty}'
    assert renderer.render_directive_attributes({'key': 'needs space'}) == '{key="needs space"}'
    assert quote_directive_attribute('') == '""'
    assert quote_directive_attribute('simple') == 'simple'
    assert delimiter_for_align('left') == ':---'
    assert delimiter_for_align('right') == '---:'
    assert delimiter_for_align('center') == ':---:'
    assert delimiter_for_align(None) == '---'
    assert normalize_table_row(Text(value='not-row'), 2) == [TableCell(), TableCell()]
    assert normalize_table_row(TableRow(children=[TableCell(), TableCell()]), 1) == [TableCell()]
