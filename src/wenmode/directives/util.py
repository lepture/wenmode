from __future__ import annotations

from wenmode.nodes import ContainerDirective, Node, Paragraph


def split_directive_label(node: ContainerDirective) -> tuple[Paragraph | None, list[Node]]:
    """Split a container directive into its label paragraph and body nodes."""
    if node.children and isinstance(node.children[0], Paragraph) and node.children[0].data == {'directiveLabel': True}:
        return node.children[0], node.children[1:]
    return None, node.children


def append_class(current: str | None, value: str) -> str:
    """Append one CSS class value to an existing class attribute."""
    return f'{current} {value}' if current else value
