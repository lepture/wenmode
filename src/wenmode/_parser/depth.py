from __future__ import annotations

from wenmode.nodes import Node, Parent

SCAFFOLDING_TYPES = frozenset(
    {'root', 'paragraph', 'heading', 'listItem', 'definitionTerm', 'definitionDescription', 'tableRow', 'tableCell'}
)


def semantic_container_depth(node: Node) -> int:
    """Count content wrappers, excluding structural block scaffolding."""
    return int(isinstance(node, Parent) and node.type not in SCAFFOLDING_TYPES)
