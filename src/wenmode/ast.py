from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from typing import TypeAlias

from .nodes import Image, Literal, Node, Parent

NodeMatcher: TypeAlias = str | type[Node] | tuple[str | type[Node], ...]
__all__ = [
    'NodeMatcher',
    'find',
    'find_all',
    'iter_children',
    'plain_text',
    'walk',
]


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
