from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, TypeAlias, cast

from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import LiteralDirective as LiteralDirectiveNode
from wenmode.nodes import Node
from wenmode.rules import BlockCandidate, BlockRule
from wenmode.rules.blocks.directive import collect_until_with_source, directive_label_children

from .._parser.state import BlockState

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

FencedDirectiveFence: TypeAlias = Iterable[str]
DEFAULT_FENCE = ('`', '~')
FENCED_DIRECTIVE_NAME_PATTERN = r'[A-Za-z][A-Za-z0-9_-]*'
ATTRIBUTE_RE = re.compile(r'[ \t]*:(?P<name>[A-Za-z][A-Za-z0-9_-]*):[ \t]*')
DEFAULT_LITERAL_DIRECTIVE_NAMES = frozenset({'code-block'})


def normalize_fence(fence: FencedDirectiveFence) -> tuple[str, ...]:
    chars = tuple(dict.fromkeys(fence))
    if not chars:
        raise ValueError('fence must include at least one character')
    for char in chars:
        if len(char) != 1:
            raise ValueError('fence entries must be single characters')
    return chars


def fence_pattern(fence: FencedDirectiveFence) -> str:
    return '|'.join(rf'{re.escape(char)}{{3,}}' for char in normalize_fence(fence))


def fenced_directive_pattern(fence: FencedDirectiveFence) -> str:
    return rf' {{0,3}}(?:{fence_pattern(fence)})\{{{FENCED_DIRECTIVE_NAME_PATTERN}\}}'


def compile_fenced_directive_re(fence: FencedDirectiveFence) -> re.Pattern[str]:
    return re.compile(
        rf'(?P<indent> {{0,3}})(?P<fence>{fence_pattern(fence)})'
        rf'\{{(?P<name>{FENCED_DIRECTIVE_NAME_PATTERN})\}}'
    )


class FencedDirectiveRule(BlockRule):
    """Parse MyST-style fenced directives such as code fences with ``{name}``."""

    name: str = 'fenced_directive'
    order: ClassVar[int] = 60
    pattern: str = fenced_directive_pattern(DEFAULT_FENCE)

    def __init__(
        self,
        literal_names: Iterable[str] = DEFAULT_LITERAL_DIRECTIVE_NAMES,
        fence: FencedDirectiveFence = DEFAULT_FENCE,
    ) -> None:
        fence_chars = normalize_fence(fence)
        super().__init__(pattern=fenced_directive_pattern(fence_chars))
        self.literal_names = frozenset(literal_names)
        self._head_pattern = compile_fenced_directive_re(fence_chars)

    def parse_directive_head(self, state: BlockState) -> tuple[str, str | None, re.Pattern[str]]:
        line = state.line.rstrip('\r\n')
        opener = cast(re.Match[str], self._head_pattern.match(line))
        fence = opener.group('fence')
        fence_char = fence[0]
        name = opener.group('name')
        title = line[opener.end() :].strip() or None
        closer = re.compile(rf' {{0,3}}{re.escape(fence_char)}{{{len(fence)},}}[ \t]*$')
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
        children.extend(parser.parse_blocks(''.join(lines), parent_state=state, source=source.map()))
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

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Node | None:
        name, argument, closer = self.parse_directive_head(state)
        attributes = self.parse_directive_attributes(state)
        if name in self.literal_names:
            value = self.parse_literal_directive_body(state, closer)
            return LiteralDirectiveNode(name=name, argument=argument, attributes=attributes or None, value=value)
        children = self.parse_directive_body(parser, state, argument, closer)
        return ContainerDirectiveNode(name=name, attributes=attributes or None, children=children)


def parse_attribute_line(line: str) -> tuple[str, str] | None:
    text = line.rstrip('\r\n')
    match = ATTRIBUTE_RE.match(text)
    if match is None:
        return None
    return match.group('name'), text[match.end() :]


nodes: dict[str, type[Node]] = {}


@dataclass(frozen=True)
class FencedDirectivePlugin:
    literal_names: Iterable[str] = DEFAULT_LITERAL_DIRECTIVE_NAMES
    fence: FencedDirectiveFence = DEFAULT_FENCE

    def setup(self, wen: Wenmode, /) -> None:
        wen.register_rule(FencedDirectiveRule(literal_names=self.literal_names, fence=self.fence))


def configure(
    *, literal_names: Iterable[str] = DEFAULT_LITERAL_DIRECTIVE_NAMES, fence: FencedDirectiveFence = DEFAULT_FENCE
) -> FencedDirectivePlugin:
    return FencedDirectivePlugin(literal_names=literal_names, fence=fence)


def setup(wen: Wenmode, /) -> None:
    configure().setup(wen)
