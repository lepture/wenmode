from __future__ import annotations

import re
from typing import TYPE_CHECKING, Any, ClassVar

from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import Node
from wenmode.rules.base import BlockRule
from wenmode.rules.blocks.directive import collect_until_with_source, directive_label_children
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

FENCED_DIRECTIVE_RE = re.compile(
    r'(?P<indent>[ \t]{0,3})(?P<fence>`{3,}|~{3,})\{(?P<name>[A-Za-z][A-Za-z0-9_-]*)}(?P<title>.*)$'
)
OPTION_RE = re.compile(r'[ \t]*:([A-Za-z][A-Za-z0-9_-]*):(?:[ \t]*(.*))?$')


class FencedDirectiveRule(BlockRule):
    """Parse MyST-style fenced directives such as code fences with ``{name}``."""

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
        source = state.source.collect()
        lines = collect_until_with_source(state, source, lambda line: closer.match(line.rstrip('\r\n')) is not None)

        children = directive_label_children(parser, title, state)
        children.extend(
            parser.parse_blocks(
                ''.join(lines),
                parent_state=state,
                source=source.map(),
            )
        )
        return ContainerDirectiveNode(name=name, attributes=attributes or None, children=children)


def parse_option_line(line: str) -> tuple[str, str] | None:
    match = OPTION_RE.match(line.rstrip('\r\n'))
    if match is None:
        return None
    return match.group(1), match.group(2) or ''


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rule(FencedDirectiveRule)
