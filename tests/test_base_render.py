from __future__ import annotations

from dataclasses import dataclass

from wenmode.nodes import Literal, Parent
from wenmode.renderers import BaseRenderer, RenderContext


@dataclass
class CustomLiteral(Literal):
    type: str = 'customLiteral'


@dataclass
class CustomParent(Parent):
    type: str = 'customParent'


class CustomRenderer(BaseRenderer):
    pass


def test_renderer_registers_custom_node_handler() -> None:
    @CustomRenderer.register('customLiteral')
    def render_custom_literal(renderer: CustomRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<custom>{node.value}</custom>'

    assert CustomRenderer().render(CustomLiteral(value='<x>')) == '<custom><x></custom>'


def test_base_renderer_unknown_nodes_fall_back_to_children_or_value() -> None:
    renderer = BaseRenderer()

    assert renderer.render(CustomParent(children=[CustomLiteral(value='a'), CustomLiteral(value='b')])) == 'ab'
    assert renderer.render(CustomLiteral(value='literal')) == 'literal'
