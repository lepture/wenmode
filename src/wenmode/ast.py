from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import fields, is_dataclass
from typing import Any, TypeAlias, cast

from .nodes import (
    BUILTIN_NODES,
    Heading,
    Image,
    Literal,
    Node,
    Parent,
    Position,
)

NodeMatcher: TypeAlias = str | type[Node] | tuple[str | type[Node], ...]
UnknownNodePolicy: TypeAlias = str

__all__ = [
    'NodeMatcher',
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
    nodes: Iterable[type[Node]] | None = None,
    unknown: UnknownNodePolicy = 'generic',
    allow_internal_metadata: bool = False,
) -> Node:
    """Convert a mdast-like mapping into Wenmode nodes.

    Built-in mdast-compatible node types are restored as their concrete Wenmode
    node classes. Pass ``nodes`` as an iterable of node classes to restore
    plugin node types. Unknown nodes are preserved as generic
    :class:`~wenmode.nodes.Parent`,
    :class:`~wenmode.nodes.Literal`, or :class:`~wenmode.nodes.Node` instances by
    default; pass ``unknown="error"`` to reject them.

    Source positions are restored only when both ``position.start.offset`` and
    ``position.end.offset`` are present. Line and column values alone are not
    enough to reconstruct Wenmode's internal offset ranges.

    ``allow_internal_metadata=True`` preserves parser-internal trust metadata
    in AST data produced by a trusted Wenmode pipeline. It does not disable
    structural validation and must not be enabled for external AST input.
    """
    return node_from_ast(
        data,
        nodes=nodes,
        unknown=unknown,
        allow_internal_metadata=allow_internal_metadata,
    )


def node_from_ast(
    data: Mapping[str, Any],
    *,
    nodes: Iterable[type[Node]] | None = None,
    unknown: UnknownNodePolicy = 'generic',
    allow_internal_metadata: bool = False,
) -> Node:
    """Convert one AST node mapping into a Wenmode node.

    ``allow_internal_metadata`` is a trusted-input setting for AST data
    produced by Wenmode, not a general validation bypass.
    """
    if unknown not in {'generic', 'error'}:
        raise ValueError('unknown must be "generic" or "error"')

    node_lookup = _node_lookup(BUILTIN_NODES)
    if nodes is not None:
        node_lookup.update(_node_lookup(nodes))
    return _node_from_ast(data, node_lookup, unknown, allow_internal_metadata)


def _node_lookup(
    nodes: Iterable[type[Node]],
    *,
    error_prefix: str = 'nodes',
) -> dict[str, type[Node]]:
    result: dict[str, type[Node]] = {}
    for node_class in nodes:
        if not isinstance(node_class, type) or not issubclass(node_class, Node):
            raise TypeError(f'{error_prefix} entries must be Node classes')
        node_type = getattr(node_class, 'type', None)
        if not isinstance(node_type, str) or not node_type:
            raise TypeError(f'{error_prefix} entries must define a non-empty string type')
        result[node_type] = node_class
    return result


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


def plain_text(value: Node | Iterable[Node], *, block_separator: str = '\n') -> str:
    """Return the concatenated plain text content of a node or node sequence.

    Images contribute their ``alt`` text, literal nodes contribute ``value``,
    parent nodes contribute their children's text, and reference-like leaf nodes
    fall back to ``label`` or ``identifier`` fields. Block-level sibling nodes
    are separated with ``block_separator``.
    """
    if isinstance(value, Node):
        return _plain_text_node(value, block_separator)
    return _plain_text_nodes(value, block_separator)


def _plain_text_nodes(nodes: Iterable[Node], block_separator: str) -> str:
    parts: list[str] = []
    previous_separated = False
    for node in nodes:
        text = _plain_text_node(node, block_separator)
        if not text:
            continue
        separated = node.block
        if parts and (previous_separated or separated):
            parts.append(block_separator)
        parts.append(text)
        previous_separated = separated
    return ''.join(parts)


def _plain_text_node(node: Node, block_separator: str) -> str:
    if isinstance(node, Image):
        return node.alt
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Parent):
        return _plain_text_nodes(node.children, block_separator)
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
    node_lookup: dict[str, type[Node]],
    unknown: UnknownNodePolicy,
    allow_internal_metadata: bool,
) -> Node:
    node_type = data.get('type')
    if not isinstance(node_type, str) or not node_type:
        raise ValueError('AST node must include a non-empty string "type"')

    attrs: dict[str, Any] = {}
    for key, value in data.items():
        if key.startswith('_'):
            raise ValueError(f'AST node field "{key}" is private')
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
            children = [
                _ast_value_from_ast(item, node_lookup, unknown, allow_internal_metadata) for item in value
            ]
            if not all(isinstance(child, Node) for child in children):
                raise TypeError('AST node "children" entries must be nodes')
            attrs[key] = children
            continue
        if key == 'data':
            if value is not None and not isinstance(value, Mapping):
                raise TypeError('AST node "data" must be a mapping')
            attrs[key] = dict(value) if isinstance(value, Mapping) else value
            continue
        attrs[key] = _ast_value_from_ast(value, node_lookup, unknown, allow_internal_metadata)

    node_class = node_lookup.get(node_type)
    if node_class is None:
        if unknown == 'error':
            raise ValueError(f'unsupported AST node type: {node_type}')
        node = _generic_node_from_attrs(node_type, attrs)
    else:
        node = _construct_node(node_class, node_type, attrs)
    _validate_restored_node(
        node,
        allow_internal_metadata=allow_internal_metadata,
    )
    return node


def _ast_value_from_ast(
    value: Any,
    node_lookup: dict[str, type[Node]],
    unknown: UnknownNodePolicy,
    allow_internal_metadata: bool,
) -> Any:
    if isinstance(value, Mapping) and isinstance(value.get('type'), str):
        return _node_from_ast(value, node_lookup, unknown, allow_internal_metadata)
    if isinstance(value, list):
        return [_ast_value_from_ast(item, node_lookup, unknown, allow_internal_metadata) for item in value]
    return value


def _validate_restored_node(
    node: Node,
    *,
    allow_internal_metadata: bool,
) -> None:
    if isinstance(node, Literal) and not isinstance(node.value, str):
        raise TypeError('AST literal "value" must be a string')
    if isinstance(node, Heading):
        if type(node.depth) is not int:
            raise TypeError('AST heading "depth" must be an integer')
        if not 1 <= node.depth <= 6:
            raise ValueError('AST heading "depth" must be between 1 and 6')
    if (
        node.type in {'html', 'htmlContainer'}
        and node.data is not None
        and 'escaped' in node.data
        and not allow_internal_metadata
    ):
        raise ValueError(
            f'AST {node.type} "data.escaped" is internal metadata; '
            'pass allow_internal_metadata=True for trusted Wenmode AST data'
        )


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
