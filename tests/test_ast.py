from __future__ import annotations

from wenmode import Wenmode
from wenmode.ast import find, find_all, iter_children, plain_text, walk
from wenmode.nodes import FootnoteReference, Heading, Image, Link, Node, Paragraph, Text
from wenmode.presets import github


def test_walk_yields_nodes_in_depth_first_order() -> None:
    root = Wenmode(github).parse('# Title\n\nA [link](/url) and ![alt](/img.png).\n')

    assert [node.type for node in walk(root)] == [
        'root',
        'heading',
        'text',
        'paragraph',
        'text',
        'link',
        'text',
        'text',
        'image',
        'text',
    ]
    assert [node.type for node in walk(root, include_self=False)][:2] == ['heading', 'text']


def test_iter_children_yields_direct_child_nodes() -> None:
    paragraph = Paragraph(children=[Text(value='a'), Text(value='b')])

    assert list(iter_children(paragraph)) == paragraph.children
    assert list(iter_children(Text(value='leaf'))) == []


def test_iter_children_ignores_non_node_items() -> None:
    paragraph = Paragraph(children=[Text(value='a')])
    paragraph.children.append('not a node')

    assert list(iter_children(paragraph)) == [Text(value='a')]


def test_find_returns_first_matching_node() -> None:
    root = Wenmode().parse('# Title\n\nA [link](/url).\n')

    node = find(root, 'link')

    assert isinstance(node, Link)
    assert node.url == '/url'
    assert find(root) is root
    assert find(root, 'image') is None


def test_find_all_matches_type_strings_classes_tuples_and_predicates() -> None:
    root = Wenmode(github).parse('# Title\n\n## Deep\n\nA [link](/url) and ![alt](/img.png).\n')

    headings = find_all(root, Heading)
    media = find_all(root, ('link', 'image'))
    shallow_headings = find_all(root, Heading, predicate=lambda node: isinstance(node, Heading) and node.depth == 1)

    assert [plain_text(heading) for heading in headings] == ['Title', 'Deep']
    assert [node.type for node in media] == ['link', 'image']
    assert [plain_text(heading) for heading in shallow_headings] == ['Title']


def test_plain_text_extracts_textual_content() -> None:
    link = Link(url='/url', children=[Text(value='label')])
    image = Image(url='/img.png', alt='image alt')
    footnote = FootnoteReference(identifier='note-id', label='Note Label')
    identifier_node = Node(type='custom')
    identifier_node.identifier = 'identifier'

    assert plain_text(link) == 'label'
    assert plain_text(image) == 'image alt'
    assert plain_text(footnote) == 'Note Label'
    assert plain_text(identifier_node) == 'identifier'
    assert plain_text(Node(type='custom')) == ''
    assert plain_text([Text(value='a'), link, image]) == 'alabelimage alt'
    assert plain_text(Text(value='literal')) == 'literal'
