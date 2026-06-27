from __future__ import annotations

from dataclasses import dataclass

from wenmode import Wenmode
from wenmode.ast import find, find_all, from_ast, iter_children, plain_text, registry_from_plugins, walk
from wenmode.nodes import (
    FootnoteReference,
    Heading,
    Image,
    Link,
    LiteralDirective,
    Node,
    Paragraph,
    Parent,
    Position,
    Text,
)
from wenmode.plugins import definition_list, math, plugin
from wenmode.presets import github


@dataclass
class Callout(Parent):
    kind: str = ''
    type: str = 'callout'


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


def test_from_ast_round_trips_builtin_nodes() -> None:
    app = Wenmode(github)
    ast = app.parse('# Title\n\nA [link](/url) and ![alt](/img.png).\n\n| A | B |\n| --- | --- |\nx | y\n').to_ast()

    restored = from_ast(ast)

    assert restored.to_ast() == ast
    assert isinstance(find(restored, Heading), Heading)
    assert isinstance(find(restored, 'image'), Image)


def test_from_ast_restores_literal_directive_node() -> None:
    node = from_ast(
        {
            'type': 'literalDirective',
            'value': 'print("x")\n',
            'name': 'code-block',
            'argument': 'python',
            'attributes': {'caption': 'example.py'},
        }
    )

    assert isinstance(node, LiteralDirective)
    assert node.to_ast() == {
        'type': 'literalDirective',
        'value': 'print("x")\n',
        'name': 'code-block',
        'argument': 'python',
        'attributes': {'caption': 'example.py'},
    }


def test_from_ast_restores_offset_positions() -> None:
    node = from_ast(
        {
            'type': 'text',
            'position': {
                'start': {'line': 1, 'column': 1, 'offset': 0},
                'end': {'line': 1, 'column': 5, 'offset': 4},
            },
            'value': 'text',
        }
    )

    assert isinstance(node, Text)
    assert node.position == Position(start=0, end=4)
    assert node.to_ast() == {
        'type': 'text',
        'position': {'start': {'offset': 0}, 'end': {'offset': 4}},
        'value': 'text',
    }


def test_from_ast_ignores_positions_without_offsets() -> None:
    node = from_ast(
        {
            'type': 'text',
            'position': {
                'start': {'line': 1, 'column': 1},
                'end': {'line': 1, 'column': 5},
            },
            'value': 'text',
        }
    )

    assert node.position is None
    assert node.to_ast() == {'type': 'text', 'value': 'text'}


def test_from_ast_preserves_unknown_nodes_generically() -> None:
    ast = {
        'type': 'callout',
        'data': {'hName': 'aside'},
        'children': [
            {
                'type': 'calloutTitle',
                'value': 'Note',
                'priority': 2,
            }
        ],
        'kind': 'note',
    }

    node = from_ast(ast)

    assert isinstance(node, Parent)
    assert node.type == 'callout'
    assert node.to_ast() == ast


def test_from_ast_uses_custom_registry() -> None:
    node = from_ast(
        {
            'type': 'callout',
            'kind': 'warning',
            'children': [{'type': 'text', 'value': 'Careful'}],
        },
        registry={'callout': Callout},
    )

    assert isinstance(node, Callout)
    assert node.kind == 'warning'
    assert node.to_ast() == {
        'type': 'callout',
        'children': [{'type': 'text', 'value': 'Careful'}],
        'kind': 'warning',
    }


def test_registry_from_plugins_restores_builtin_plugin_nodes() -> None:
    ast = {
        'type': 'root',
        'children': [
            {'type': 'math', 'value': 'x + y\n'},
            {
                'type': 'definitionList',
                'children': [
                    {'type': 'definitionTerm', 'children': [{'type': 'text', 'value': 'Term'}]},
                    {
                        'type': 'definitionDescription',
                        'children': [{'type': 'paragraph', 'children': [{'type': 'text', 'value': 'Definition'}]}],
                        'spread': False,
                    },
                ],
            },
        ],
    }

    registry = registry_from_plugins([plugin(math, inline=False), definition_list])
    node = from_ast(ast, registry=registry)

    assert type(node.children[0]).__name__ == 'MathNode'
    assert type(node.children[1]).__name__ == 'DefinitionListNode'
    assert node.to_ast() == ast


def test_from_ast_can_reject_unknown_nodes() -> None:
    try:
        from_ast({'type': 'unknown'}, unknown='error')
    except ValueError as exc:
        assert str(exc) == 'unsupported AST node type: unknown'
    else:  # pragma: no cover
        raise AssertionError('from_ast should reject unknown nodes')
