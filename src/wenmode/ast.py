from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import fields, is_dataclass
from typing import Any, TypeAlias, cast

from .nodes import (
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
    Literal,
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

NodeMatcher: TypeAlias = str | type[Node] | tuple[str | type[Node], ...]
NodeRegistry: TypeAlias = Mapping[str, type[Node]]
UnknownNodePolicy: TypeAlias = str
BUILTIN_NODE_REGISTRY: dict[str, type[Node]] = {
    'root': Root,
    'paragraph': Paragraph,
    'heading': Heading,
    'blockquote': Blockquote,
    'list': List,
    'listItem': ListItem,
    'code': Code,
    'thematicBreak': ThematicBreak,
    'html': Html,
    'text': Text,
    'inlineCode': InlineCode,
    'strong': Strong,
    'emphasis': Emphasis,
    'delete': Delete,
    'table': Table,
    'tableRow': TableRow,
    'tableCell': TableCell,
    'link': Link,
    'image': Image,
    'break': Break,
    'footnoteReference': FootnoteReference,
    'footnoteDefinition': FootnoteDefinition,
    'textDirective': TextDirective,
    'leafDirective': LeafDirective,
    'containerDirective': ContainerDirective,
    'literalDirective': LiteralDirective,
}
__all__ = [
    'BUILTIN_NODE_REGISTRY',
    'NodeMatcher',
    'NodeRegistry',
    'UnknownNodePolicy',
    'find',
    'find_all',
    'from_ast',
    'iter_children',
    'node_from_ast',
    'plain_text',
    'walk',
]


def from_ast(
    data: Mapping[str, Any],
    *,
    registry: NodeRegistry | None = None,
    unknown: UnknownNodePolicy = 'generic',
) -> Node:
    """Convert a mdast-like mapping into Wenmode nodes.

    Built-in mdast-compatible node types are restored as their concrete Wenmode
    node classes. Pass ``registry`` to restore plugin node types. Unknown nodes
    are preserved as generic :class:`~wenmode.nodes.Parent`,
    :class:`~wenmode.nodes.Literal`, or :class:`~wenmode.nodes.Node` instances by
    default; pass ``unknown="error"`` to reject them.

    Source positions are restored only when both ``position.start.offset`` and
    ``position.end.offset`` are present. Line and column values alone are not
    enough to reconstruct Wenmode's internal offset ranges.
    """
    return node_from_ast(data, registry=registry, unknown=unknown)


def node_from_ast(
    data: Mapping[str, Any],
    *,
    registry: NodeRegistry | None = None,
    unknown: UnknownNodePolicy = 'generic',
) -> Node:
    """Convert one AST node mapping into a Wenmode node."""
    if unknown not in {'generic', 'error'}:
        raise ValueError('unknown must be "generic" or "error"')

    node_registry = dict(BUILTIN_NODE_REGISTRY)
    if registry is not None:
        node_registry.update(registry)
    return _node_from_ast(data, node_registry, unknown)


def iter_children(node: Node) -> Iterator[Node]:
    """Yield direct child nodes from a node.

    The helper follows the mdast-style ``children`` field used by Wenmode's
    parent nodes and by plugin nodes that follow the same convention.
    """
    children = getattr(node, 'children', None)
    if not isinstance(children, list):
        return
    for child in children:
        if isinstance(child, Node):
            yield child


def walk(node: Node, *, include_self: bool = True) -> Iterator[Node]:
    """Yield nodes in depth-first, pre-order traversal.

    :param node: Root or subtree to traverse.
    :param include_self: Yield ``node`` before its descendants when ``True``.
    :returns: Iterator over nodes.
    """
    if include_self:
        yield node
    for child in iter_children(node):
        yield from walk(child)


def find(
    node: Node,
    type: NodeMatcher | None = None,
    *,
    predicate: Callable[[Node], bool] | None = None,
    include_self: bool = True,
) -> Node | None:
    """Return the first matching node in depth-first order.

    ``type`` may be a node ``type`` string, a node class, a tuple of strings or
    classes, or ``None`` to match every node.
    """
    for candidate in walk(node, include_self=include_self):
        if _matches(candidate, type) and (predicate is None or predicate(candidate)):
            return candidate
    return None


def find_all(
    node: Node,
    type: NodeMatcher | None = None,
    *,
    predicate: Callable[[Node], bool] | None = None,
    include_self: bool = True,
) -> list[Node]:
    """Return all matching nodes in depth-first order.

    ``type`` may be a node ``type`` string, a node class, a tuple of strings or
    classes, or ``None`` to match every node.
    """
    return [
        candidate
        for candidate in walk(node, include_self=include_self)
        if _matches(candidate, type) and (predicate is None or predicate(candidate))
    ]


def plain_text(value: Node | Iterable[Node]) -> str:
    """Return the concatenated plain text content of a node or node sequence.

    Images contribute their ``alt`` text, literal nodes contribute ``value``,
    parent nodes contribute their children's text, and reference-like leaf nodes
    fall back to ``label`` or ``identifier`` fields.
    """
    if isinstance(value, Node):
        return _plain_text_node(value)
    return ''.join(_plain_text_node(node) for node in value)


def _plain_text_node(node: Node) -> str:
    if isinstance(node, Image):
        return node.alt
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Parent):
        return ''.join(_plain_text_node(child) for child in node.children)
    label = getattr(node, 'label', None)
    if isinstance(label, str):
        return label
    identifier = getattr(node, 'identifier', None)
    if isinstance(identifier, str):
        return identifier
    return ''


def _matches(node: Node, matcher: NodeMatcher | None) -> bool:
    if matcher is None:
        return True
    if isinstance(matcher, tuple):
        return any(_matches(node, item) for item in matcher)
    if isinstance(matcher, str):
        return node.type == matcher
    return isinstance(node, matcher)


def _node_from_ast(
    data: Mapping[str, Any],
    registry: dict[str, type[Node]],
    unknown: UnknownNodePolicy,
) -> Node:
    node_type = data.get('type')
    if not isinstance(node_type, str) or not node_type:
        raise ValueError('AST node must include a non-empty string "type"')

    attrs: dict[str, Any] = {}
    for key, value in data.items():
        if key == 'type':
            continue
        if key == 'position':
            position = _position_from_ast(value)
            if position is not None:
                attrs[key] = position
            continue
        if key == 'children':
            if not isinstance(value, list):
                raise TypeError('AST node "children" must be a list')
            attrs[key] = [_ast_value_from_ast(item, registry, unknown) for item in value]
            continue
        if key == 'data':
            attrs[key] = dict(value) if isinstance(value, Mapping) else value
            continue
        attrs[key] = _ast_value_from_ast(value, registry, unknown)

    node_class = registry.get(node_type)
    if node_class is None:
        if unknown == 'error':
            raise ValueError(f'unsupported AST node type: {node_type}')
        return _generic_node_from_attrs(node_type, attrs)
    return _construct_node(node_class, node_type, attrs)


def _ast_value_from_ast(value: Any, registry: dict[str, type[Node]], unknown: UnknownNodePolicy) -> Any:
    if isinstance(value, Mapping) and isinstance(value.get('type'), str):
        return _node_from_ast(value, registry, unknown)
    if isinstance(value, list):
        return [_ast_value_from_ast(item, registry, unknown) for item in value]
    return value


def _position_from_ast(value: Any) -> Position | None:
    if not isinstance(value, Mapping):
        return None
    start = value.get('start')
    end = value.get('end')
    if not isinstance(start, Mapping) or not isinstance(end, Mapping):
        return None
    start_offset = start.get('offset')
    end_offset = end.get('offset')
    if not isinstance(start_offset, int) or not isinstance(end_offset, int):
        return None
    return Position(start=start_offset, end=end_offset)


def _construct_node(node_class: type[Node], node_type: str, attrs: dict[str, Any]) -> Node:
    init_fields = _init_field_names(node_class)
    init_kwargs: dict[str, Any] = {}
    if 'type' in init_fields:
        init_kwargs['type'] = node_type
    for key, value in attrs.items():
        if key in init_fields:
            init_kwargs[key] = value

    node = cast(Node, cast(Any, node_class)(**init_kwargs))
    for key, value in attrs.items():
        if key not in init_fields:
            setattr(node, key, value)
    return node


def _init_field_names(node_class: type[Node]) -> set[str]:
    if not is_dataclass(node_class):
        return {'type', 'data', 'position'}
    return {field.name for field in fields(node_class) if field.init}


def _generic_node_from_attrs(node_type: str, attrs: dict[str, Any]) -> Node:
    init_kwargs = _base_init_kwargs(node_type, attrs)
    if isinstance(attrs.get('children'), list):
        node: Node = Parent(children=cast(list[Node], attrs['children']), **init_kwargs)
        consumed = {'type', 'data', 'position', 'children'}
    elif isinstance(attrs.get('value'), str):
        node = Literal(value=attrs['value'], **init_kwargs)
        consumed = {'type', 'data', 'position', 'value'}
    else:
        node = Node(**init_kwargs)
        consumed = {'type', 'data', 'position'}

    for key, value in attrs.items():
        if key not in consumed:
            setattr(node, key, value)
    return node


def _base_init_kwargs(node_type: str, attrs: dict[str, Any]) -> dict[str, Any]:
    kwargs: dict[str, Any] = {'type': node_type}
    if 'data' in attrs:
        kwargs['data'] = attrs['data']
    if 'position' in attrs:
        kwargs['position'] = attrs['position']
    return kwargs
