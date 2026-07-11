from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import pytest

from tests.ast_fixtures import (
    BUILTIN_NODE_SHAPES,
    PLUGIN_NODE_SAMPLES,
    PLUGIN_REGISTRY_TARGETS,
    PLUGIN_ROUND_TRIP_MARKDOWN,
    PLUGIN_ROUND_TRIP_NODE_TYPES,
    PLUGIN_ROUND_TRIP_TARGETS,
)
from wenmode import Wenmode
from wenmode.ast import find, find_all, from_ast, iter_children, plain_text, walk
from wenmode.nodes import (
    BUILTIN_NODES,
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
from wenmode.plugins import block_math, definition_list, html_container
from wenmode.presets import github


@dataclass
class Callout(Parent):
    kind: str = ''
    type: str = 'callout'


@dataclass
class PluginContainer(Parent):
    type: str = 'pluginContainer'


def collect_plugin_nodes(plugins: list[object]) -> list[type[Node]]:
    nodes: list[type[Node]] = []
    for plugin in plugins:
        nodes.extend(getattr(plugin, 'nodes', []))
    return nodes


def node_chain(depth: int, node_type: str = 'paragraph') -> dict[str, object]:
    ast: dict[str, object] = {'type': node_type, 'children': []}
    current = ast
    for _index in range(depth - 1):
        child: dict[str, object] = {'type': node_type, 'children': []}
        current['children'] = [child]
        current = child
    return ast


@pytest.mark.parametrize(
    ('node_type', 'node_class', 'ast'),
    BUILTIN_NODE_SHAPES,
    ids=[node_type for node_type, _node_class, _ast in BUILTIN_NODE_SHAPES],
)
def test_from_ast_round_trips_builtin_node_shapes(node_type: str, node_class: type[Node], ast: dict) -> None:
    node = from_ast(ast, allow_internal_metadata=True)

    assert {node.type: node for node in BUILTIN_NODES}[node_type] is node_class
    assert isinstance(node, node_class)
    assert node.to_ast() == ast


@pytest.mark.parametrize(
    ('node_type', 'node_class', 'ast'),
    PLUGIN_NODE_SAMPLES,
    ids=[node_type for node_type, _node_class, _ast in PLUGIN_NODE_SAMPLES],
)
def test_from_ast_round_trips_plugin_node_shapes(node_type: str, node_class: type[Node], ast: dict) -> None:
    nodes = collect_plugin_nodes(PLUGIN_REGISTRY_TARGETS)
    node = from_ast(ast, nodes=nodes, allow_internal_metadata=True)

    assert {node.type: node for node in nodes}[node_type] is node_class
    assert isinstance(node, node_class)
    assert node.to_ast() == ast


def test_builtin_plugins_expose_node_lists() -> None:
    nodes = collect_plugin_nodes(PLUGIN_REGISTRY_TARGETS)

    assert {node.type: node for node in nodes} == {
        node_type: node_class for node_type, node_class, _ast in PLUGIN_NODE_SAMPLES
    }


def test_parsed_plugin_ast_round_trips_through_plugin_registry() -> None:
    app = Wenmode(github, plugins=PLUGIN_ROUND_TRIP_TARGETS)

    ast = app.parse(PLUGIN_ROUND_TRIP_MARKDOWN).to_ast()
    restored = from_ast(ast, nodes=collect_plugin_nodes(PLUGIN_ROUND_TRIP_TARGETS))

    assert restored.to_ast() == ast
    assert {node.type for node in walk(restored)} >= PLUGIN_ROUND_TRIP_NODE_TYPES


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


def test_plain_text_separates_block_siblings() -> None:
    root = Wenmode().parse(' blah \n\nbblah')

    assert plain_text(root) == 'blah\nbblah'
    assert plain_text(root.children) == 'blah\nbblah'
    assert plain_text(root, block_separator='\n\n') == 'blah\n\nbblah'
    assert plain_text(root, block_separator='') == 'blahbblah'


def test_plain_text_keeps_inline_children_concatenated() -> None:
    root = Wenmode(github).parse('# A *strong* [link](/url)\n\n- first\n- second\n')
    heading = find(root, Heading)

    assert heading is not None
    assert plain_text(heading) == 'A strong link'
    assert plain_text(root) == 'A strong link\nfirst\nsecond'


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
            'position': {'start': {'line': 1, 'column': 1, 'offset': 0}, 'end': {'line': 1, 'column': 5, 'offset': 4}},
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
            'position': {'start': {'line': 1, 'column': 1}, 'end': {'line': 1, 'column': 5}},
            'value': 'text',
        }
    )

    assert node.position is None
    assert node.to_ast() == {'type': 'text', 'value': 'text'}


def test_from_ast_preserves_unknown_nodes_generically() -> None:
    ast = {
        'type': 'callout',
        'data': {'hName': 'aside'},
        'children': [{'type': 'calloutTitle', 'value': 'Note', 'priority': 2}],
        'kind': 'note',
    }

    node = from_ast(ast)

    assert isinstance(node, Parent)
    assert node.type == 'callout'
    assert node.to_ast() == ast


def test_from_ast_enforces_max_depth_boundary() -> None:
    assert from_ast(node_chain(4), max_depth=4).to_ast() == node_chain(4)

    with pytest.raises(ValueError, match='^AST exceeds maximum depth of 4$'):
        from_ast(node_chain(5), max_depth=4)


def test_from_ast_enforces_max_node_count_boundary() -> None:
    exact = {'type': 'root', 'children': [{'type': 'text', 'value': str(index)} for index in range(4)]}
    too_many = {'type': 'root', 'children': [{'type': 'text', 'value': str(index)} for index in range(5)]}

    assert from_ast(exact, max_nodes=5).to_ast() == exact
    with pytest.raises(ValueError, match='^AST exceeds maximum node count of 5$'):
        from_ast(too_many, max_nodes=5)


def test_from_ast_counts_unknown_generic_and_plugin_nodes_identically() -> None:
    generic = node_chain(4, 'unknownContainer')
    plugin = node_chain(4, 'pluginContainer')

    assert from_ast(generic, max_nodes=4).to_ast() == generic
    assert from_ast(plugin, nodes=[PluginContainer], max_nodes=4).to_ast() == plugin

    with pytest.raises(ValueError, match='^AST exceeds maximum node count of 3$'):
        from_ast(generic, max_nodes=3)
    with pytest.raises(ValueError, match='^AST exceeds maximum node count of 3$'):
        from_ast(plugin, nodes=[PluginContainer], max_nodes=3)


def test_from_ast_rejects_child_path_reference_cycle() -> None:
    ast: dict[str, object] = {'type': 'paragraph', 'children': []}
    child: dict[str, object] = {'type': 'paragraph', 'children': [ast]}
    ast['children'] = [child]

    with pytest.raises(ValueError, match='^AST contains a reference cycle$'):
        from_ast(ast)


def test_from_ast_rejects_list_cycle_in_extension_field() -> None:
    values: list[object] = []
    values.append(values)
    ast = {'type': 'custom', 'values': values}

    with pytest.raises(ValueError, match='^AST contains a reference cycle$'):
        from_ast(ast)


def test_from_ast_rejects_data_mapping_cycle() -> None:
    data: dict[str, object] = {}
    data['self'] = data
    ast = {'type': 'custom', 'data': data}

    with pytest.raises(ValueError, match='^AST contains a reference cycle$'):
        from_ast(ast)


def test_from_ast_allows_shared_acyclic_containers() -> None:
    shared_child = {'type': 'text', 'value': 'same'}
    shared_metadata = {'label': ['same']}
    ast = {
        'type': 'root',
        'children': [
            {'type': 'paragraph', 'children': [shared_child], 'data': shared_metadata},
            {'type': 'paragraph', 'children': [shared_child], 'data': shared_metadata},
        ],
    }

    assert from_ast(ast).to_ast() == ast


@pytest.mark.parametrize('limit_name', ['max_depth', 'max_nodes'])
@pytest.mark.parametrize('limit', [True, False, 1.5, '2'])
def test_from_ast_rejects_invalid_limit_types(limit_name: str, limit: object) -> None:
    with pytest.raises(TypeError, match=f'^{limit_name} must be an integer or None$'):
        if limit_name == 'max_depth':
            from_ast({'type': 'root', 'children': []}, max_depth=cast(Any, limit))
        else:
            from_ast({'type': 'root', 'children': []}, max_nodes=cast(Any, limit))


@pytest.mark.parametrize('limit_name', ['max_depth', 'max_nodes'])
@pytest.mark.parametrize('limit', [0, -1])
def test_from_ast_rejects_invalid_limit_values(limit_name: str, limit: int) -> None:
    with pytest.raises(ValueError, match=f'^{limit_name} must be a positive integer or None$'):
        if limit_name == 'max_depth':
            from_ast({'type': 'root', 'children': []}, max_depth=limit)
        else:
            from_ast({'type': 'root', 'children': []}, max_nodes=limit)


def test_from_ast_none_disables_selected_budget_only() -> None:
    assert from_ast(node_chain(5), max_depth=None, max_nodes=5).to_ast() == node_chain(5)
    assert from_ast(node_chain(5), max_depth=5, max_nodes=None).to_ast() == node_chain(5)

    with pytest.raises(ValueError, match='^AST exceeds maximum node count of 4$'):
        from_ast(node_chain(5), max_depth=None, max_nodes=4)
    with pytest.raises(ValueError, match='^AST exceeds maximum depth of 4$'):
        from_ast(node_chain(5), max_depth=4, max_nodes=None)


def test_from_ast_none_limits_do_not_disable_cycles_or_structural_validation() -> None:
    data: dict[str, object] = {}
    data['self'] = data
    with pytest.raises(ValueError, match='^AST contains a reference cycle$'):
        from_ast({'type': 'custom', 'data': data}, max_depth=None, max_nodes=None)

    with pytest.raises(TypeError, match='^AST heading "depth" must be an integer$'):
        from_ast({'type': 'heading', 'depth': True, 'children': []}, max_depth=None, max_nodes=None)


def test_from_ast_uses_custom_registry() -> None:
    node = from_ast(
        {'type': 'callout', 'kind': 'warning', 'children': [{'type': 'text', 'value': 'Careful'}]}, nodes=[Callout]
    )

    assert isinstance(node, Callout)
    assert node.kind == 'warning'
    assert node.to_ast() == {'type': 'callout', 'children': [{'type': 'text', 'value': 'Careful'}], 'kind': 'warning'}


def test_from_ast_rejects_mapping_registry() -> None:
    with pytest.raises(TypeError, match='nodes entries must be Node classes'):
        from_ast({'type': 'callout', 'kind': 'warning'}, nodes={'callout': Callout})


def test_from_ast_restores_builtin_plugin_nodes() -> None:
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

    nodes = [*block_math.nodes, *definition_list.nodes]
    node = from_ast(ast, nodes=nodes)

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


@pytest.mark.parametrize('child', ['text', {'value': 'missing type'}])
def test_from_ast_rejects_non_node_children(child: object) -> None:
    with pytest.raises(TypeError, match='^AST node "children" entries must be nodes$'):
        from_ast({'type': 'paragraph', 'children': [child]})


def test_from_ast_rejects_non_string_literal_value() -> None:
    with pytest.raises(TypeError, match='^AST literal "value" must be a string$'):
        from_ast({'type': 'text', 'value': 1})


@pytest.mark.parametrize('start', [True, 1.5, 'not-a-number', {'value': 2}])
def test_from_ast_rejects_non_integer_list_start(start: object) -> None:
    with pytest.raises(TypeError, match='^AST list "start" must be an integer or null$'):
        from_ast({'type': 'list', 'ordered': True, 'start': start, 'spread': False, 'children': []})


@pytest.mark.parametrize('start', [None, 0, 2, -1])
def test_from_ast_accepts_integer_or_null_list_start(start: int | None) -> None:
    ast = {'type': 'list', 'ordered': True, 'start': start, 'spread': False, 'children': []}
    expected = {'type': 'list', 'ordered': True, 'spread': False, 'children': []}
    if start is not None:
        expected['start'] = start

    node = from_ast(ast)

    assert node.to_ast() == expected


@pytest.mark.parametrize('depth', [True, 1.0, '1'])
def test_from_ast_rejects_non_integer_heading_depth(depth: object) -> None:
    with pytest.raises(TypeError, match='^AST heading "depth" must be an integer$'):
        from_ast({'type': 'heading', 'depth': depth, 'children': []})


@pytest.mark.parametrize('depth', [0, 7])
def test_from_ast_rejects_out_of_range_heading_depth(depth: int) -> None:
    with pytest.raises(ValueError, match='^AST heading "depth" must be between 1 and 6$'):
        from_ast({'type': 'heading', 'depth': depth, 'children': []})


def test_from_ast_rejects_non_mapping_data() -> None:
    with pytest.raises(TypeError, match='^AST node "data" must be a mapping$'):
        from_ast({'type': 'text', 'value': 'safe', 'data': 'untrusted'})


def test_from_ast_rejects_private_fields() -> None:
    with pytest.raises(ValueError, match='^AST node field "_private" is private$'):
        from_ast({'type': 'text', 'value': 'safe', '_private': 'untrusted'})


def test_from_ast_rejects_internal_html_metadata_by_default() -> None:
    with pytest.raises(
        ValueError,
        match=(
            '^AST html "data.escaped" is internal metadata; '
            'pass allow_internal_metadata=True for trusted Wenmode AST data$'
        ),
    ):
        from_ast({'type': 'html', 'value': '<em>safe</em>', 'data': {'escaped': True}})


def test_from_ast_allows_internal_html_metadata_for_trusted_ast() -> None:
    ast = {'type': 'html', 'value': '&lt;em&gt;safe&lt;/em&gt;', 'data': {'escaped': True}}

    node = from_ast(ast, allow_internal_metadata=True)

    assert node.to_ast() == ast


def test_allow_internal_metadata_does_not_bypass_structural_validation() -> None:
    with pytest.raises(TypeError, match='^AST heading "depth" must be an integer$'):
        from_ast({'type': 'heading', 'depth': True, 'children': []}, allow_internal_metadata=True)


def test_from_ast_rejects_internal_html_container_metadata_by_default() -> None:
    with pytest.raises(
        ValueError,
        match=(
            '^AST htmlContainer "data.escaped" is internal metadata; '
            'pass allow_internal_metadata=True for trusted Wenmode AST data$'
        ),
    ):
        from_ast(
            {
                'type': 'htmlContainer',
                'data': {'escaped': True},
                'children': [],
                'name': 'div',
                'opening': '&lt;div&gt;',
                'closing': '&lt;/div&gt;',
            },
            nodes=html_container.nodes,
        )


def test_from_ast_rejects_internal_metadata_on_generic_html_container() -> None:
    with pytest.raises(
        ValueError,
        match=(
            '^AST htmlContainer "data.escaped" is internal metadata; '
            'pass allow_internal_metadata=True for trusted Wenmode AST data$'
        ),
    ):
        from_ast(
            {
                'type': 'htmlContainer',
                'data': {'escaped': True},
                'children': [],
                'opening': '<script>',
                'closing': '</script>',
            }
        )


def test_from_ast_preserves_internal_metadata_on_unrelated_unknown_node() -> None:
    ast = {'type': 'customContainer', 'data': {'escaped': True}, 'children': []}

    node = from_ast(ast)

    assert type(node) is Parent
    assert node.to_ast() == ast
