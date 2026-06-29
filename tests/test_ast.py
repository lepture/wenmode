from __future__ import annotations

from dataclasses import dataclass

import pytest

from wenmode import Wenmode
from wenmode.ast import (
    BUILTIN_NODE_REGISTRY,
    find,
    find_all,
    from_ast,
    iter_children,
    plain_text,
    registry_from_plugins,
    walk,
)
from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    ContainerDirective,
    Delete,
    Emphasis,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    LeafDirective,
    Link,
    List,
    ListItem,
    LiteralDirective,
    Node,
    Paragraph,
    Parent,
    Position,
    Root,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    TextDirective,
    ThematicBreak,
)
from wenmode.plugins import (
    abbr,
    definition_list,
    fenced_directive,
    frontmatter,
    html_container,
    inline_role,
    insert,
    mark,
    math,
    plugin,
    ruby,
    spoiler,
    subscript,
    superscript,
)
from wenmode.presets import github


@dataclass
class Callout(Parent):
    kind: str = ''
    type: str = 'callout'


TEXT_AST = {'type': 'text', 'value': 'text'}
INLINE_TEXT_AST = {'type': 'text', 'value': 'inline'}
PARAGRAPH_AST = {'type': 'paragraph', 'children': [TEXT_AST]}

BUILTIN_NODE_SHAPES = [
    (
        'root',
        Root,
        {'type': 'root', 'children': [PARAGRAPH_AST]},
    ),
    (
        'paragraph',
        Paragraph,
        PARAGRAPH_AST,
    ),
    (
        'heading',
        Heading,
        {'type': 'heading', 'children': [TEXT_AST], 'depth': 2},
    ),
    (
        'blockquote',
        Blockquote,
        {'type': 'blockquote', 'children': [PARAGRAPH_AST]},
    ),
    (
        'list',
        List,
        {
            'type': 'list',
            'children': [
                {
                    'type': 'listItem',
                    'children': [PARAGRAPH_AST],
                    'checked': False,
                    'spread': True,
                }
            ],
            'ordered': True,
            'start': 3,
            'spread': True,
        },
    ),
    (
        'listItem',
        ListItem,
        {'type': 'listItem', 'children': [PARAGRAPH_AST], 'checked': True, 'spread': False},
    ),
    (
        'code',
        Code,
        {'type': 'code', 'value': 'print(1)\n', 'lang': 'python', 'meta': 'linenos'},
    ),
    (
        'thematicBreak',
        ThematicBreak,
        {'type': 'thematicBreak'},
    ),
    (
        'html',
        Html,
        {'type': 'html', 'data': {'escaped': True}, 'value': '&lt;script>alert(1)&lt;/script>\n'},
    ),
    (
        'text',
        Text,
        TEXT_AST,
    ),
    (
        'inlineCode',
        InlineCode,
        {'type': 'inlineCode', 'value': 'code'},
    ),
    (
        'strong',
        Strong,
        {'type': 'strong', 'children': [INLINE_TEXT_AST]},
    ),
    (
        'emphasis',
        Emphasis,
        {'type': 'emphasis', 'children': [INLINE_TEXT_AST]},
    ),
    (
        'delete',
        Delete,
        {'type': 'delete', 'children': [INLINE_TEXT_AST]},
    ),
    (
        'table',
        Table,
        {
            'type': 'table',
            'children': [
                {
                    'type': 'tableRow',
                    'children': [
                        {'type': 'tableCell', 'children': [TEXT_AST]},
                        {'type': 'tableCell', 'children': [INLINE_TEXT_AST]},
                    ],
                }
            ],
            'align': ['left', None],
        },
    ),
    (
        'tableRow',
        TableRow,
        {'type': 'tableRow', 'children': [{'type': 'tableCell', 'children': [TEXT_AST]}]},
    ),
    (
        'tableCell',
        TableCell,
        {'type': 'tableCell', 'children': [TEXT_AST]},
    ),
    (
        'link',
        Link,
        {'type': 'link', 'children': [TEXT_AST], 'url': '/url', 'title': 'Title'},
    ),
    (
        'image',
        Image,
        {'type': 'image', 'url': '/img.png', 'alt': 'Alt text', 'title': 'Title'},
    ),
    (
        'break',
        Break,
        {'type': 'break'},
    ),
    (
        'footnoteReference',
        FootnoteReference,
        {'type': 'footnoteReference', 'identifier': 'note-id', 'label': 'Note Label'},
    ),
    (
        'footnoteDefinition',
        FootnoteDefinition,
        {'type': 'footnoteDefinition', 'children': [PARAGRAPH_AST], 'identifier': 'note-id', 'label': 'Note Label'},
    ),
    (
        'textDirective',
        TextDirective,
        {'type': 'textDirective', 'children': [TEXT_AST], 'name': 'abbr', 'attributes': {'title': 'Full name'}},
    ),
    (
        'leafDirective',
        LeafDirective,
        {'type': 'leafDirective', 'children': [TEXT_AST], 'name': 'youtube', 'attributes': {'id': 'abc'}},
    ),
    (
        'containerDirective',
        ContainerDirective,
        {'type': 'containerDirective', 'children': [PARAGRAPH_AST], 'name': 'note', 'attributes': {'class': 'wide'}},
    ),
    (
        'literalDirective',
        LiteralDirective,
        {
            'type': 'literalDirective',
            'value': 'print("*literal*")\n',
            'name': 'code-block',
            'argument': 'python',
            'attributes': {'caption': 'example.py'},
        },
    ),
]

PLUGIN_NODE_SAMPLES = [
    (
        'abbreviation',
        abbr.AbbreviationNode,
        {'type': 'abbreviation', 'children': [TEXT_AST], 'title': 'HyperText Markup Language'},
    ),
    (
        'definitionList',
        definition_list.DefinitionListNode,
        {
            'type': 'definitionList',
            'children': [
                {'type': 'definitionTerm', 'children': [TEXT_AST]},
                {
                    'type': 'definitionDescription',
                    'children': [PARAGRAPH_AST],
                    'spread': False,
                },
            ],
        },
    ),
    (
        'definitionTerm',
        definition_list.DefinitionTermNode,
        {'type': 'definitionTerm', 'children': [TEXT_AST]},
    ),
    (
        'definitionDescription',
        definition_list.DefinitionDescriptionNode,
        {'type': 'definitionDescription', 'children': [PARAGRAPH_AST], 'spread': True},
    ),
    (
        'htmlContainer',
        html_container.HtmlContainerNode,
        {
            'type': 'htmlContainer',
            'data': {'escaped': True},
            'children': [PARAGRAPH_AST],
            'name': 'div',
            'attributes': {'id': 'steps', 'hidden': True},
            'opening': '<div id="steps" hidden>',
            'closing': '</div>',
        },
    ),
    (
        'math',
        math.MathNode,
        {'type': 'math', 'value': 'x + y\n'},
    ),
    (
        'inlineMath',
        math.InlineMathNode,
        {'type': 'inlineMath', 'value': 'x + y'},
    ),
    (
        'blockSpoiler',
        spoiler.BlockSpoilerNode,
        {'type': 'blockSpoiler', 'children': [PARAGRAPH_AST]},
    ),
    (
        'inlineSpoiler',
        spoiler.InlineSpoilerNode,
        {'type': 'inlineSpoiler', 'children': [TEXT_AST]},
    ),
    (
        'mark',
        mark.MarkNode,
        {'type': 'mark', 'children': [TEXT_AST]},
    ),
    (
        'insert',
        insert.InsertNode,
        {'type': 'insert', 'children': [TEXT_AST]},
    ),
    (
        'superscript',
        superscript.SuperscriptNode,
        {'type': 'superscript', 'children': [TEXT_AST]},
    ),
    (
        'subscript',
        subscript.SubscriptNode,
        {'type': 'subscript', 'children': [TEXT_AST]},
    ),
    (
        'ruby',
        ruby.RubyNode,
        {'type': 'ruby', 'segments': [{'base': '漢字', 'text': 'kanji'}]},
    ),
]

PLUGIN_REGISTRY_TARGETS = [
    abbr,
    definition_list,
    fenced_directive,
    frontmatter,
    html_container,
    inline_role,
    insert,
    mark,
    plugin(math, inline=False),
    ruby,
    spoiler,
    subscript,
    superscript,
]


@pytest.mark.parametrize(
    ('node_type', 'node_class', 'ast'),
    BUILTIN_NODE_SHAPES,
    ids=[node_type for node_type, _node_class, _ast in BUILTIN_NODE_SHAPES],
)
def test_from_ast_round_trips_builtin_node_shapes(node_type: str, node_class: type[Node], ast: dict) -> None:
    node = from_ast(ast)

    assert BUILTIN_NODE_REGISTRY[node_type] is node_class
    assert isinstance(node, node_class)
    assert node.to_ast() == ast


@pytest.mark.parametrize(
    ('node_type', 'node_class', 'ast'),
    PLUGIN_NODE_SAMPLES,
    ids=[node_type for node_type, _node_class, _ast in PLUGIN_NODE_SAMPLES],
)
def test_from_ast_round_trips_plugin_node_shapes(node_type: str, node_class: type[Node], ast: dict) -> None:
    registry = registry_from_plugins(PLUGIN_REGISTRY_TARGETS)
    node = from_ast(ast, registry=registry)

    assert registry[node_type] is node_class
    assert isinstance(node, node_class)
    assert node.to_ast() == ast


def test_registry_from_plugins_collects_all_builtin_plugin_nodes() -> None:
    registry = registry_from_plugins(PLUGIN_REGISTRY_TARGETS)

    assert registry == {node_type: node_class for node_type, node_class, _ast in PLUGIN_NODE_SAMPLES}


def test_parsed_plugin_ast_round_trips_through_plugin_registry() -> None:
    plugins = [
        frontmatter,
        html_container,
        abbr,
        definition_list,
        fenced_directive,
        inline_role,
        insert,
        mark,
        math,
        ruby,
        spoiler,
        subscript,
        superscript,
    ]
    app = Wenmode(github, plugins=plugins)
    markdown = '''---
title: AST contract
---

The HTML spec uses ==mark==, ^^insert^^, H~2~O, 2^10^, [漢字(kanji)], >! secret !<,
$x + y$, and {abbr}`CPU`.

*[HTML]: HyperText Markup Language

Apple
: *fruit*

>! hidden *thing*

<div id="steps" hidden>
- one
</div>

$$
x + y
$$

```{code-block} python
print("*literal*")
```
'''

    ast = app.parse(markdown).to_ast()
    restored = from_ast(ast, registry=registry_from_plugins(plugins))

    assert restored.to_ast() == ast
    assert {node.type for node in walk(restored)} >= {
        'root',
        'abbreviation',
        'definitionList',
        'definitionTerm',
        'definitionDescription',
        'htmlContainer',
        'mark',
        'insert',
        'subscript',
        'superscript',
        'ruby',
        'inlineSpoiler',
        'blockSpoiler',
        'inlineMath',
        'math',
        'textDirective',
        'literalDirective',
    }


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
