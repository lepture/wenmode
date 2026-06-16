from __future__ import annotations

from wenmode.nodes import ContainerDirective, Node, Paragraph


def split_directive_label(node: ContainerDirective) -> tuple[Paragraph | None, list[Node]]:
    if node.children and isinstance(node.children[0], Paragraph) and node.children[0].data == {'directiveLabel': True}:
        return node.children[0], node.children[1:]
    return None, node.children
