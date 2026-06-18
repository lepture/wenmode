from __future__ import annotations

from dataclasses import dataclass

from wenmode import HTMLRenderer, Wenmode
from wenmode.nodes import Paragraph, Parent, Text
from wenmode.renderers import RenderContext
from wenmode.rules import Footnote


@dataclass
class CustomElement(Parent):
    type: str = 'customElement'


def test_html_renderer_custom_elements_require_registered_handler() -> None:
    node = Paragraph(children=[CustomElement(children=[Text(value='marked')])])

    assert HTMLRenderer().render(node) == '<p>marked</p>\n'

    @HTMLRenderer.register('customElement')
    def render_custom_element(renderer: HTMLRenderer, node: CustomElement, context: RenderContext) -> str:
        attrs = renderer.render_attrs({'data-custom': 'yes', 'hidden': False})
        return f'<mark{attrs}>{renderer.render_children(node.children, context)}</mark>'

    assert HTMLRenderer().render(node) == '<p><mark data-custom="yes">marked</mark></p>\n'


def test_html_renderer_reuses_instance_without_leaking_footnote_state() -> None:
    app = Wenmode([Footnote])
    renderer = HTMLRenderer()
    root = app.parse('a[^one]\n\n[^one]: note\n')

    first = renderer.render(root)
    second = renderer.render(root)

    assert second == first
    assert 'id="user-content-fnref-one-2"' not in second
