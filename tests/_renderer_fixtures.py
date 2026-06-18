from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

from wenmode.nodes import (
    Abbreviation,
    Blockquote,
    BlockSpoiler,
    Break,
    Code,
    ContainerDirective,
    DefinitionDescription,
    DefinitionList,
    DefinitionTerm,
    Delete,
    Emphasis,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    InlineMath,
    InlineSpoiler,
    Insert,
    LeafDirective,
    Link,
    List,
    ListItem,
    Mark,
    Math,
    Node,
    Paragraph,
    Parent,
    Root,
    Ruby,
    Strong,
    Subscript,
    Superscript,
    Table,
    TableCell,
    TableRow,
    Text,
    TextDirective,
    ThematicBreak,
)

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
NODE_TYPES = {
    'abbreviation': Abbreviation,
    'blockquote': Blockquote,
    'blockSpoiler': BlockSpoiler,
    'break': Break,
    'code': Code,
    'containerDirective': ContainerDirective,
    'definitionDescription': DefinitionDescription,
    'definitionList': DefinitionList,
    'definitionTerm': DefinitionTerm,
    'delete': Delete,
    'emphasis': Emphasis,
    'footnoteDefinition': FootnoteDefinition,
    'footnoteReference': FootnoteReference,
    'heading': Heading,
    'html': Html,
    'image': Image,
    'inlineCode': InlineCode,
    'inlineMath': InlineMath,
    'inlineSpoiler': InlineSpoiler,
    'insert': Insert,
    'leafDirective': LeafDirective,
    'link': Link,
    'list': List,
    'listItem': ListItem,
    'mark': Mark,
    'math': Math,
    'paragraph': Paragraph,
    'root': Root,
    'ruby': Ruby,
    'strong': Strong,
    'subscript': Subscript,
    'superscript': Superscript,
    'table': Table,
    'tableCell': TableCell,
    'tableRow': TableRow,
    'text': Text,
    'textDirective': TextDirective,
    'thematicBreak': ThematicBreak,
}


class RendererExample(TypedDict, total=False):
    name: str
    node: dict[str, Any]
    output: str
    options: dict[str, Any]
    footnote_definitions: bool


def load_renderer_examples(name: str) -> list[RendererExample]:
    return json.loads((FIXTURES_DIR / name).read_text())


def node_from_ast(data: dict[str, Any]) -> Node:
    node_type = data['type']
    node_class = NODE_TYPES.get(node_type)
    if node_class is None:
        return Node(type=node_type, data=data.get('data'))

    kwargs = {key: value for key, value in data.items() if key != 'type'}
    children = kwargs.get('children')
    if isinstance(children, list):
        kwargs['children'] = [node_from_ast(child) for child in children]
    return node_class(**kwargs)


def node_from_renderer_example(example: RendererExample) -> Node:
    node = node_from_ast(example['node'])
    if example.get('footnote_definitions') and isinstance(node, Root):
        node.footnote_definitions = {
            child.identifier: child for child in node.children if isinstance(child, FootnoteDefinition)
        }
    return node


def render_children_node(children: list[Node]) -> Parent:
    return Parent(type='parent', children=children)
