from __future__ import annotations

import pytest

from wenmode import RSTRenderer
from wenmode.nodes import Image, Root, Text

from ._renderer_fixtures import RendererExample, load_renderer_examples, node_from_renderer_example


@pytest.mark.parametrize(
    'example',
    load_renderer_examples('rst_render.json'),
    ids=lambda example: example['name'],
)
def test_rst_renderer_examples(example: RendererExample) -> None:
    assert RSTRenderer().render(node_from_renderer_example(example)) == example['output']


def test_rst_renderer_edge_branches_for_empty_and_direct_nodes() -> None:
    renderer = RSTRenderer()

    context = renderer.create_context(Root())
    assert renderer.render(Image(url='/collected.png'), context) == '|image-1|'
    assert renderer.render(Root(), context) == '.. |image-1| image:: /collected.png\n'


def test_rst_renderer_directive_edge_branches() -> None:
    renderer = RSTRenderer()

    assert renderer.render_directive_argument(Text(value='ignored'), renderer.create_context()) == ''
