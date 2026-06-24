from __future__ import annotations

import re
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, ClassVar, cast

from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import LiteralDirective as LiteralDirectiveNode
from wenmode.nodes import Node
from wenmode.rules.base import BlockRule
from wenmode.rules.blocks.directive import collect_until_with_source, directive_label_children
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

FENCED_DIRECTIVE_RE = re.compile(r'(?P<indent>[ \t]{0,3})(?P<fence>`{3,}|~{3,})\{(?P<name>[A-Za-z][A-Za-z0-9_-]*)}')
ATTRIBUTE_RE = re.compile(r'[ \t]*:(?P<name>[A-Za-z][A-Za-z0-9_-]*):[ \t]*')
DEFAULT_LITERAL_DIRECTIVE_NAMES = frozenset({'code-block'})


class FencedDirectiveRule(BlockRule):
    """Parse MyST-style fenced directives such as code fences with ``{name}``."""

    name: str = 'fenced_directive'
    order: ClassVar[int] = 60
    pattern: str = r'[ \t]{0,3}(?:`{3,}|~{3,})\{[A-Za-z][A-Za-z0-9_-]*}'
    head_pattern: ClassVar[re.Pattern[str]] = FENCED_DIRECTIVE_RE

    def __init__(self, literal_names: Iterable[str] = DEFAULT_LITERAL_DIRECTIVE_NAMES) -> None:
        super().__init__()
        self.literal_names = frozenset(literal_names)

    @staticmethod
    def parse_directive_head(state: BlockState, pattern: re.Pattern[str]) -> tuple[str, str | None, re.Pattern[str]]:
        line = state.line.rstrip('\r\n')
        opener = cast(re.Match[str], pattern.match(line))
        fence = opener.group('fence')
        fence_char = fence[0]
        name = opener.group('name')
        title = line[opener.end() :].strip() or None
        closer = re.compile(rf'[ \t]{{0,3}}{re.escape(fence_char)}{{{len(fence)},}}[ \t]*$')
        state.advance()
        return name, title, closer

    @staticmethod
    def parse_directive_attributes(state: BlockState) -> dict[str, str] | None:
        attributes: dict[str, str] = {}
        while not state.done:
            option = parse_attribute_line(state.line)
            if option is None:
                break
            key, value = option
            attributes[key] = value
            state.advance()

        if not state.done and state.line.strip() == '':
            state.advance()
        return attributes

    @staticmethod
    def parse_directive_body(
        parser: Parser, state: BlockState, title: str | None, closer: re.Pattern[str]
    ) -> list[Node]:
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
        return children

    @staticmethod
    def parse_literal_directive_body(state: BlockState, closer: re.Pattern[str]) -> str:
        lines: list[str] = []
        while not state.done:
            line = state.line
            if closer.match(line.rstrip('\r\n')) is not None:
                state.advance()
                break
            lines.append(line)
            state.advance()
        return ''.join(lines)

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        name, argument, closer = self.parse_directive_head(state, self.head_pattern)
        attributes = self.parse_directive_attributes(state)
        if name in self.literal_names:
            value = self.parse_literal_directive_body(state, closer)
            return LiteralDirectiveNode(
                name=name,
                argument=argument,
                attributes=attributes or None,
                value=value,
            )
        children = self.parse_directive_body(parser, state, argument, closer)
        return ContainerDirectiveNode(name=name, attributes=attributes or None, children=children)


def parse_attribute_line(line: str) -> tuple[str, str] | None:
    text = line.rstrip('\r\n')
    match = ATTRIBUTE_RE.match(text)
    if match is None:
        return None
    return match.group('name'), text[match.end() :]


def setup(
    wenmode: Wenmode,
    literal_names: Iterable[str] = DEFAULT_LITERAL_DIRECTIVE_NAMES,
    **options: Any,
) -> None:
    wenmode.register_rule(FencedDirectiveRule(literal_names=literal_names))
