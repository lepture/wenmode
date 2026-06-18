from __future__ import annotations

from dataclasses import dataclass

import pytest

from wenmode import HTMLRenderer, Wenmode
from wenmode.directives import Admonition, Figure, TableOfContents
from wenmode.nodes import (
    ContainerDirective,
    FootnoteDefinition,
    FootnoteReference,
    LeafDirective,
    Node,
    Paragraph,
    Parent,
    Root,
    Text,
)
from wenmode.renderers import RenderContext
from wenmode.rules import Footnote

from ._renderer_fixtures import RendererExample, load_renderer_examples, node_from_renderer_example


@dataclass
class CustomElement(Parent):
    type: str = 'customElement'


def root_with_footnote_definitions(children: list[Node]) -> Root:
    root = Root(children=children)
    root.footnote_definitions = {child.identifier: child for child in children if isinstance(child, FootnoteDefinition)}
    return root


@pytest.mark.parametrize(
    'example',
    load_renderer_examples('html_render.json'),
    ids=lambda example: example['name'],
)
def test_html_renderer_examples(example: RendererExample) -> None:
    renderer = HTMLRenderer(**example.get('options', {}))

    assert renderer.render(node_from_renderer_example(example)) == example['output']


def test_html_renderer_custom_elements_require_registered_handler() -> None:
    node = Paragraph(children=[CustomElement(children=[Text(value='marked')])])

    assert HTMLRenderer().render(node) == '<p>marked</p>\n'

    @HTMLRenderer.register('customElement')
    def render_custom_element(renderer: HTMLRenderer, node: CustomElement, context: RenderContext) -> str:
        attrs = renderer.render_attrs({'data-custom': 'yes', 'hidden': False})
        return f'<mark{attrs}>{renderer.render_children(node.children, context)}</mark>'

    assert HTMLRenderer().render(node) == '<p><mark data-custom="yes">marked</mark></p>\n'


def test_html_renderer_orders_multiple_footnotes_by_first_reference() -> None:
    node = root_with_footnote_definitions(
        [
            FootnoteDefinition(identifier='one', label='one', children=[Paragraph(children=[Text(value='one')])]),
            FootnoteDefinition(identifier='two', label='two', children=[Paragraph(children=[Text(value='two')])]),
            Paragraph(
                children=[
                    FootnoteReference(identifier='two', label='two'),
                    Text(value=' '),
                    FootnoteReference(identifier='one', label='one'),
                ]
            ),
        ]
    )

    html = HTMLRenderer().render(node)

    assert html.index('<li id="user-content-fn-two">') < html.index('<li id="user-content-fn-one">')
    assert 'id="user-content-fnref-two" data-footnote-ref aria-describedby="footnote-label">1</a>' in html
    assert 'id="user-content-fnref-one" data-footnote-ref aria-describedby="footnote-label">2</a>' in html


def test_html_renderer_reuses_number_for_repeated_footnote_references() -> None:
    node = root_with_footnote_definitions(
        [
            Paragraph(
                children=[
                    FootnoteReference(identifier='one', label='one'),
                    Text(value=' '),
                    FootnoteReference(identifier='one', label='one'),
                ]
            ),
            FootnoteDefinition(identifier='one', label='one', children=[Paragraph(children=[Text(value='note')])]),
        ]
    )

    html = HTMLRenderer().render(node)

    assert html.count('aria-describedby="footnote-label">1</a></sup>') == 2
    assert 'id="user-content-fnref-one-2"' in html
    assert 'href="#user-content-fnref-one-2" data-footnote-backref' in html


def test_html_renderer_reuses_instance_without_leaking_footnote_state() -> None:
    app = Wenmode([Footnote])
    renderer = HTMLRenderer()
    root = app.parse('a[^one]\n\n[^one]: note\n')

    first = renderer.render(root)
    second = renderer.render(root)

    assert second == first
    assert 'id="user-content-fnref-one-2"' not in second


def test_html_renderer_escapes_footnotes() -> None:
    node = root_with_footnote_definitions(
        [
            Paragraph(children=[FootnoteReference(identifier='a<b', label='a<b')]),
            FootnoteDefinition(identifier='a<b', label='a<b', children=[Paragraph(children=[Text(value='<note>')])]),
        ]
    )

    html = HTMLRenderer().render(node)

    assert 'href="#user-content-fn-a%3Cb"' in html
    assert '<p>&lt;note&gt; <a href="#user-content-fnref-a%3Cb"' in html


def test_html_renderer_edge_branches() -> None:
    renderer = HTMLRenderer()
    context = renderer.create_context()

    assert renderer.render_attrs({'disabled': True, 'hidden': False, 'skip': None}) == ' disabled'
    assert renderer.render_list_item(Text(value='raw'), loose=False, context=context) == 'raw'

    empty_context = renderer.create_context()
    assert renderer.render_footnote_section(empty_context) == ''
    missing_context = renderer.create_context()
    missing_context.footnotes.order.append('missing')
    assert renderer.render_footnote_section(missing_context) == (
        '<section data-footnotes class="footnotes">\n'
        '<h2 class="sr-only" id="footnote-label">Footnotes</h2>\n'
        '<ol>\n'
        '</ol>\n</section>\n'
    )
    assert renderer.render_footnote_definition_content(FootnoteDefinition(children=[Text(value='loose')]), context) == (
        'loose'
    )
    assert renderer.render(FootnoteReference(identifier='missing', label='<missing>')) == '[^&lt;missing&gt;]'


def test_html_directive_renderers_without_labels_and_toc_fallbacks() -> None:
    renderer = HTMLRenderer(directives=[Admonition(), Figure(), TableOfContents()])
    root = Root(
        children=[
            ContainerDirective(name='note', children=[Paragraph(children=[Text(value='body')])]),
            ContainerDirective(name='figure', children=[Paragraph(children=[Text(value='image')])]),
            LeafDirective(name='toc', attributes={'min': 'bad'}, children=[Text(value='Contents')]),
        ]
    )

    assert renderer.render(root) == (
        '<aside class="admonition admonition-note">\n<p>body</p>\n</aside>\n<figure>\n<p>image</p>\n</figure>\n'
    )
    assert TableOfContents().render(HTMLRenderer(), LeafDirective(name='toc'), renderer.create_context()) == ''
