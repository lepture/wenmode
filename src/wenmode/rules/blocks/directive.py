from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import LeafDirective as LeafDirectiveNode
from wenmode.nodes import Node, Paragraph
from wenmode.state import BlockState

from ..base import BlockRule
from ..directives import parse_directive_head
from .util import collect_until

if TYPE_CHECKING:
    from wenmode.parser import Parser


CONTAINER_DIRECTIVE_RE = re.compile(r'(?P<indent>[ \t]{0,3})(?P<fence>:{3,})(?P<head>.*)$')
FENCED_DIRECTIVE_RE = re.compile(
    r'(?P<indent>[ \t]{0,3})(?P<fence>`{3,}|~{3,})\{(?P<name>[A-Za-z][A-Za-z0-9_-]*)}(?P<title>.*)$'
)
OPTION_RE = re.compile(r'[ \t]*:([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$')


class LeafDirective(BlockRule):
    """Parse mdast-style leaf directives such as ``::name[label]``.

    Markdown syntax:

    .. code-block:: markdown

       ::toc[On this page]{min=2 max=3}
    """

    def __init__(self) -> None:
        super().__init__('leaf_directive', r'[ \t]{0,3}::(?=[A-Za-z])')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        line = state.line.rstrip('\r\n')
        head = parse_leaf_directive_head(line)
        if head is None:
            return None

        parsed = parse_directive_head(head, 0)
        if parsed is None:
            return None
        name, label, attributes, end = parsed
        if head[end:].strip():
            return None

        state.advance()
        children = parser.parse_inlines(label, state) if label is not None else []
        return LeafDirectiveNode(name=name, attributes=attributes, children=children)


class ContainerDirective(BlockRule):
    """Parse mdast-style container directives fenced with colons.

    Markdown syntax:

    .. code-block:: markdown

       :::note[Title]
       Body.
       :::
    """

    def __init__(self) -> None:
        super().__init__('container_directive', r'[ \t]{0,3}:{3,}(?=[A-Za-z])')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        opener = CONTAINER_DIRECTIVE_RE.match(state.line.rstrip('\r\n'))
        if opener is None:
            return None

        fence = opener.group('fence')
        parsed = parse_directive_head(opener.group('head'), 0)
        if parsed is None:
            return None
        name, label, attributes, end = parsed
        if opener.group('head')[end:].strip():
            return None

        state.advance()
        closer = re.compile(rf'[ \t]{{0,3}}:{{{len(fence)},}}[ \t]*$')
        lines = collect_until(state, lambda line: closer.match(line.rstrip('\r\n')) is not None)

        children = directive_label_children(parser, label, state)
        children.extend(parser.parse_blocks(''.join(lines), parent_state=state))
        return ContainerDirectiveNode(name=name, attributes=attributes, children=children)


class FencedDirective(BlockRule):
    """Parse MyST-style fenced directives such as code fences with ``{name}``.

    Markdown syntax:

    .. code-block:: markdown

       ```{note} Title
       Body.
       ```
    """

    order: ClassVar[int] = 60

    def __init__(self) -> None:
        super().__init__('fenced_directive', r'[ \t]{0,3}(?:`{3,}|~{3,})\{[A-Za-z][A-Za-z0-9_-]*}')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        opener = FENCED_DIRECTIVE_RE.match(state.line.rstrip('\r\n'))
        if opener is None:
            return None

        fence = opener.group('fence')
        fence_char = fence[0]
        name = opener.group('name')
        title = opener.group('title').strip() or None
        state.advance()

        attributes: dict[str, str] = {}
        while not state.done:
            option = parse_option_line(state.line)
            if option is None:
                break
            key, value = option
            attributes[key] = value
            state.advance()

        if not state.done and state.line.strip() == '':
            state.advance()

        closer = re.compile(rf'[ \t]{{0,3}}{re.escape(fence_char)}{{{len(fence)},}}[ \t]*$')
        lines = collect_until(state, lambda line: closer.match(line.rstrip('\r\n')) is not None)

        children = directive_label_children(parser, title, state)
        children.extend(parser.parse_blocks(''.join(lines), parent_state=state))
        return ContainerDirectiveNode(name=name, attributes=attributes or None, children=children)


def directive_label_children(parser: Parser, label: str | None, state: BlockState) -> list[Node]:
    if label is None:
        return []
    return [Paragraph(children=parser.parse_inlines(label, state), data={'directiveLabel': True})]


def parse_leaf_directive_head(line: str) -> str | None:
    index = 0
    while index < len(line) and index < 3 and line[index] in {' ', '\t'}:
        index += 1
    if not line.startswith('::', index):
        return None

    head = line[index + 2 :]
    if not head or not head[0].isalpha() or not head[0].isascii():
        return None
    return head.rstrip(' \t')


def parse_option_line(line: str) -> tuple[str, str] | None:
    match = OPTION_RE.match(line.rstrip('\r\n'))
    if match is None:
        return None
    return match.group(1), match.group(2) or ''
