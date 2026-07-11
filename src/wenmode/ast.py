from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass, field, fields, is_dataclass
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
from .nodes import (
    List as ListNode,
)

NodeMatcher: TypeAlias = str | type[Node] | tuple[str | type[Node], ...]
UnknownNodePolicy: TypeAlias = str
_DEFAULT_MAX_DEPTH = 100
_DEFAULT_MAX_NODES = 100_000

__all__ = [
    'NodeMatcher',
    'UnknownNodePolicy',
    'find',
    'find_all',
    'from_ast',
    'iter_children',
    'plain_text',
    'walk',
]


@dataclass
class _RestorationContext:
    node_lookup: dict[str, type[Node]]
    unknown: UnknownNodePolicy
    allow_internal_metadata: bool
    max_depth: int | None
    max_nodes: int | None
    node_count: int = 0
    active_containers: set[int] = field(default_factory=set)


def from_ast(
    data: Mapping[str, Any],
    *,
    nodes: Iterable[type[Node]] | None = None,
    unknown: UnknownNodePolicy = 'generic',
    allow_internal_metadata: bool = False,
    max_depth: int | None = _DEFAULT_MAX_DEPTH,
    max_nodes: int | None = _DEFAULT_MAX_NODES,
) -> Node:
    """Convert a mdast-like mapping into Wenmode nodes.

    Pass plugin node classes with ``nodes``. Unknown node types are preserved as
    generic nodes by default; use ``unknown="error"`` to reject them.

    Restoration validates structure, applies depth and node-count limits, and
    only preserves internal metadata when ``allow_internal_metadata=True``.
    """
    if unknown not in {'generic', 'error'}:
        raise ValueError('unknown must be "generic" or "error"')
    max_depth = _validate_restoration_limit('max_depth', max_depth)
    max_nodes = _validate_restoration_limit('max_nodes', max_nodes)

    node_lookup = _node_lookup(BUILTIN_NODES)
    if nodes is not None:
        node_lookup.update(_node_lookup(nodes))
    context = _RestorationContext(
        node_lookup=node_lookup,
        unknown=unknown,
        allow_internal_metadata=allow_internal_metadata,
        max_depth=max_depth,
        max_nodes=max_nodes,
    )
    return _restore_ast_node(data, context, 1)


def _validate_restoration_limit(name: str, value: int | None) -> int | None:
    if value is None:
        return None
    if type(value) is not int:
        raise TypeError(f'{name} must be an integer or None')
    if value <= 0:
        raise ValueError(f'{name} must be a positive integer or None')
    return value


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


def _restore_ast_node(
    data: Mapping[str, Any],
    context: _RestorationContext,
    depth: int,
) -> Node:
    if context.max_depth is not None and depth > context.max_depth:
        raise ValueError(f'AST exceeds maximum depth of {context.max_depth}')
    if context.max_nodes is not None and context.node_count >= context.max_nodes:
        raise ValueError(f'AST exceeds maximum node count of {context.max_nodes}')
    context.node_count += 1

    token = _enter_container(data, context)
    try:
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
                position = _position_from_ast(value, context)
                if position is not None:
                    attrs[key] = position
                continue
            if key == 'children':
                if not isinstance(value, list):
                    raise TypeError('AST node "children" must be a list')
                children = _ast_list_from_ast(value, context, depth)
                if not all(isinstance(child, Node) for child in children):
                    raise TypeError('AST node "children" entries must be nodes')
                attrs[key] = children
                continue
            if key == 'data':
                if value is not None and not isinstance(value, Mapping):
                    raise TypeError('AST node "data" must be a mapping')
                attrs[key] = _plain_mapping_from_ast(value, context) if isinstance(value, Mapping) else value
                continue
            attrs[key] = _ast_value_from_ast(value, context, depth)

        node_class = context.node_lookup.get(node_type)
        if node_class is None:
            if context.unknown == 'error':
                raise ValueError(f'unsupported AST node type: {node_type}')
            node = _generic_node_from_attrs(node_type, attrs)
        else:
            node = _construct_node(node_class, node_type, attrs)
        _validate_restored_node(
            node,
            allow_internal_metadata=context.allow_internal_metadata,
        )
        return node
    finally:
        _leave_container(token, context)


def _ast_value_from_ast(
    value: Any,
    context: _RestorationContext,
    depth: int,
) -> Any:
    if isinstance(value, Mapping) and isinstance(value.get('type'), str):
        return _restore_ast_node(value, context, depth + 1)
    if isinstance(value, Mapping):
        return _ast_mapping_from_ast(value, context, depth)
    if isinstance(value, list):
        return _ast_list_from_ast(value, context, depth)
    return value


def _ast_mapping_from_ast(
    value: Mapping[str, Any],
    context: _RestorationContext,
    depth: int,
) -> dict[str, Any]:
    token = _enter_container(value, context)
    try:
        return {key: _ast_value_from_ast(item, context, depth) for key, item in value.items()}
    finally:
        _leave_container(token, context)


def _ast_list_from_ast(
    value: list[Any],
    context: _RestorationContext,
    depth: int,
) -> list[Any]:
    token = _enter_container(value, context)
    try:
        return [_ast_value_from_ast(item, context, depth) for item in value]
    finally:
        _leave_container(token, context)


def _plain_value_from_ast(value: Any, context: _RestorationContext) -> Any:
    if isinstance(value, Mapping):
        return _plain_mapping_from_ast(value, context)
    if isinstance(value, list):
        return _plain_list_from_ast(value, context)
    return value


def _plain_mapping_from_ast(
    value: Mapping[str, Any],
    context: _RestorationContext,
) -> dict[str, Any]:
    token = _enter_container(value, context)
    try:
        return {key: _plain_value_from_ast(item, context) for key, item in value.items()}
    finally:
        _leave_container(token, context)


def _plain_list_from_ast(value: list[Any], context: _RestorationContext) -> list[Any]:
    token = _enter_container(value, context)
    try:
        return [_plain_value_from_ast(item, context) for item in value]
    finally:
        _leave_container(token, context)


def _enter_container(value: Mapping[str, Any] | list[Any], context: _RestorationContext) -> int:
    token = id(value)
    if token in context.active_containers:
        raise ValueError('AST contains a reference cycle')
    context.active_containers.add(token)
    return token


def _leave_container(token: int, context: _RestorationContext) -> None:
    context.active_containers.remove(token)


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
    if isinstance(node, ListNode) and node.start is not None and type(node.start) is not int:
        raise TypeError('AST list "start" must be an integer or null')
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


def _position_from_ast(value: Any, context: _RestorationContext) -> Position | None:
    if not isinstance(value, Mapping):
        return None
    token = _enter_container(value, context)
    try:
        start_offset = _position_offset_from_ast(value.get('start'), context)
        end_offset = _position_offset_from_ast(value.get('end'), context)
        if not isinstance(start_offset, int) or not isinstance(end_offset, int):
            return None
        return Position(start=start_offset, end=end_offset)
    finally:
        _leave_container(token, context)


def _position_offset_from_ast(value: Any, context: _RestorationContext) -> Any:
    if not isinstance(value, Mapping):
        return None
    token = _enter_container(value, context)
    try:
        return value.get('offset')
    finally:
        _leave_container(token, context)


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
