from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Literal as LiteralNode
from wenmode.nodes import Node, Parent
from wenmode.rules.base import BlockRule
from wenmode.rules.blocks.util import collect_until

from .._parser.state import BlockState
from .spec import BlockFenced

if TYPE_CHECKING:
    from wenmode.parser import Parser


def _block_rule_from_syntax(syntax: BlockFenced) -> BlockRule:
    return _BlockFencedRule(syntax)


class _BlockFencedRule(BlockRule):
    """Runtime block rule generated from a ``BlockFenced`` spec."""

    def __init__(self, syntax: BlockFenced) -> None:
        self.syntax = syntax
        self._opener_re = _opener_pattern(syntax)
        self._closer_re = _closer_pattern(syntax)
        super().__init__(
            name=syntax.name,
            pattern=rf'[ \t]{{0,3}}{re.escape(syntax.opener)}',
        )

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        syntax = self.syntax
        opener_content = _parse_opener_content(state.line, syntax, self._opener_re)
        if opener_content is None:
            return None

        lines: list[str] = []
        if opener_content:
            lines.append(opener_content)
            if not opener_content.endswith('\n'):
                lines.append('\n')

        state.advance()
        lines.extend(collect_until(state, lambda line: self._closer_re.match(line.rstrip('\r\n')) is not None))

        value = ''.join(lines)
        if syntax.strip_content:
            value = value.strip()
        return _create_fenced_node(parser, state, value, syntax)


def _parse_opener_content(line: str, syntax: BlockFenced, opener_re: re.Pattern[str]) -> str | None:
    text = line.rstrip('\r\n')
    match = opener_re.match(text)
    if match is None:
        return None

    rest = match.group('rest')
    if not syntax.allow_opener_content and rest.strip():
        return None
    if syntax.allow_opener_content:
        return rest.lstrip(' \t')
    return ''


def _opener_pattern(syntax: BlockFenced) -> re.Pattern[str]:
    return re.compile(rf'^[ \t]{{0,3}}{re.escape(syntax.opener)}(?P<rest>.*)$')


def _closer_pattern(syntax: BlockFenced) -> re.Pattern[str]:
    closer = syntax.closer or syntax.opener
    return re.compile(rf'^[ \t]{{0,3}}{re.escape(closer)}[ \t]*$')


def _create_fenced_node(parser: Parser, state: BlockState, value: str, syntax: BlockFenced) -> Node:
    node_class = syntax.node
    if syntax.content == 'value':
        if not issubclass(node_class, LiteralNode):
            raise TypeError(f'{syntax.name!r} requires a Literal node for value content')
        node_factory = cast(Callable[..., Node], node_class)
        return node_factory(value=value)

    if syntax.content == 'children':
        if not issubclass(node_class, Parent):
            raise TypeError(f'{syntax.name!r} requires a Parent node for children content')
        node_factory = cast(Callable[..., Node], node_class)
        return node_factory(children=parser.parse_blocks(value, state))

    raise TypeError(f'{syntax.name!r} uses unsupported content mode {syntax.content!r}')
