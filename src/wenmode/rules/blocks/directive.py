from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import LeafDirective as LeafDirectiveNode
from wenmode.nodes import Node, Paragraph
from wenmode.rules.base import BlockRule
from wenmode.rules.directives import parse_directive_head
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


LEAF_DIRECTIVE_RE = re.compile(r'[ \t]{0,3}::(?=[A-Za-z])(.+?)[ \t]*$')
CONTAINER_DIRECTIVE_RE = re.compile(r'(?P<indent>[ \t]{0,3})(?P<fence>:{3,})(?P<head>.*)$')
FENCED_DIRECTIVE_RE = re.compile(r'(?P<indent>[ \t]{0,3})(?P<fence>`{3,}|~{3,})\{(?P<name>[A-Za-z][A-Za-z0-9_-]*)}(?P<title>.*)$')
OPTION_RE = re.compile(r'[ \t]*:([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$')


class LeafDirective(BlockRule):
    def __init__(self) -> None:
        super().__init__('leaf_directive', r'[ \t]{0,3}::(?=[A-Za-z])')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Node | None:
        line = state.line.rstrip('\r\n')
        leaf = LEAF_DIRECTIVE_RE.match(line)
        if leaf is None:
            return None

        parsed = parse_directive_head(leaf.group(1), 0)
        if parsed is None:
            return None
        name, label, attributes, end = parsed
        if leaf.group(1)[end:].strip():
            return None

        state.advance()
        children = parser.parse_inlines(label, state) if label is not None else []
        return LeafDirectiveNode(name=name, attributes=attributes, children=children)


class ContainerDirective(BlockRule):
    def __init__(self) -> None:
        super().__init__('container_directive', r'[ \t]{0,3}:{3,}(?=[A-Za-z])')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Node | None:
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
        lines: list[str] = []
        closer = re.compile(rf'[ \t]{{0,3}}:{{{len(fence)},}}[ \t]*$')
        while not state.done:
            if closer.match(state.line.rstrip('\r\n')):
                state.advance()
                break
            lines.append(state.line)
            state.advance()

        children = directive_label_children(parser, label, state)
        children.extend(parser.parse_blocks(''.join(lines), parent_state=state))
        return ContainerDirectiveNode(name=name, attributes=attributes, children=children)


class FencedDirective(BlockRule):
    order: ClassVar[int] = 50

    def __init__(self) -> None:
        super().__init__('fenced_directive', r'[ \t]{0,3}(?:`{3,}|~{3,})\{[A-Za-z][A-Za-z0-9_-]*}')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Node | None:
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

        lines: list[str] = []
        closer = re.compile(rf'[ \t]{{0,3}}{re.escape(fence_char)}{{{len(fence)},}}[ \t]*$')
        while not state.done:
            if closer.match(state.line.rstrip('\r\n')):
                state.advance()
                break
            lines.append(state.line)
            state.advance()

        children = directive_label_children(parser, title, state)
        children.extend(parser.parse_blocks(''.join(lines), parent_state=state))
        return ContainerDirectiveNode(name=name, attributes=attributes or None, children=children)


def directive_label_children(parser: Wenmode, label: str | None, state: BlockState) -> list[Node]:
    if label is None:
        return []
    return [Paragraph(children=parser.parse_inlines(label, state), data={'directiveLabel': True})]


def parse_option_line(line: str) -> tuple[str, str] | None:
    match = OPTION_RE.match(line.rstrip('\r\n'))
    if match is None:
        return None
    return match.group(1), match.group(2) or ''
