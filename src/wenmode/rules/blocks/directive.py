from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import LeafDirective as LeafDirectiveNode
from wenmode.nodes import Node, Paragraph

from ..._parser.source import SourceCollector
from ..._parser.state import BlockState
from ..base import BlockRule
from ..directives import parse_directive_head

if TYPE_CHECKING:
    from wenmode.parser import Parser


CONTAINER_DIRECTIVE_RE = re.compile(r'(?P<indent> {0,3})(?P<fence>:{3,})')


class LeafDirective(BlockRule):
    """Parse mdast-style leaf directives such as ``::name[label]``.

    Markdown syntax:

    .. code-block:: markdown

       ::toc[On this page]{min=2 max=3}
    """

    name = 'leaf_directive'
    pattern = r' {0,3}::(?=[A-Za-z])'

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        line = state.line.rstrip('\r\n')
        head = cast(str, parse_leaf_directive_head(line))
        parsed = parse_directive_head(head, 0)
        if parsed is None:
            return None
        name, label, attributes, end = parsed
        if head[end:].strip():
            return None

        state.advance()
        if label is not None:
            children = parser.parse_inlines(label, state)
        else:
            children = []
        return LeafDirectiveNode(name=name, attributes=attributes, children=children)


class ContainerDirective(BlockRule):
    """Parse mdast-style container directives fenced with colons.

    Markdown syntax:

    .. code-block:: markdown

       :::note[Title]
       Body.
       :::
    """

    name = 'container_directive'
    pattern = r' {0,3}:{3,}(?=[A-Za-z])'

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        line = state.line.rstrip('\r\n')
        opener = cast(re.Match[str], CONTAINER_DIRECTIVE_RE.match(line))
        fence = opener.group('fence')
        head = line[opener.end() :]
        parsed = parse_directive_head(head, 0)
        if parsed is None:
            return None
        name, label, attributes, end = parsed
        if head[end:].strip():
            return None

        state.advance()
        closer = re.compile(rf' {{0,3}}:{{{len(fence)},}}[ \t]*$')
        source = state.source.collect()
        lines = collect_until_with_source(state, source, lambda line: closer.match(line.rstrip('\r\n')) is not None)

        children = directive_label_children(parser, label, state)
        children.extend(parser.parse_blocks(''.join(lines), parent_state=state, source=source.map()))
        return ContainerDirectiveNode(name=name, attributes=attributes, children=children)


def directive_label_children(parser: Parser, label: str | None, state: BlockState) -> list[Node]:
    if label is None:
        return []
    return [Paragraph(children=parser.parse_inlines(label, state), data={'directiveLabel': True})]


def parse_leaf_directive_head(line: str) -> str | None:
    index = 0
    while index < len(line) and index < 3 and line[index] == ' ':
        index += 1
    if not line.startswith('::', index):
        return None

    head = line[index + 2 :]
    if not head or not head[0].isalpha() or not head[0].isascii():
        return None
    return head.rstrip(' \t')


def collect_until_with_source(
    state: BlockState, source: SourceCollector, is_closer: Callable[[str], bool]
) -> list[str]:
    lines: list[str] = []
    while not state.done:
        line = state.line
        if is_closer(line):
            state.advance()
            break
        lines.append(line)
        source.add(state.index, 0, line)
        state.advance()
    return lines
