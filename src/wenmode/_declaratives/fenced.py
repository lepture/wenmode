from __future__ import annotations

"""Configurable fenced block rules."""

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, Literal, TypeAlias, cast

from wenmode.nodes import Literal as LiteralNode
from wenmode.nodes import Node, Parent
from wenmode.rules.base import BlockRule
from wenmode.rules.blocks.util import collect_until

from .._parser.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser

FencedNodeFactory = Callable[['Parser', BlockState, str], Node]
ContentMode: TypeAlias = Literal['children', 'value']


class BlockFenced(BlockRule):
    """Configurable rule for literal fenced blocks."""

    def __init__(
        self,
        *,
        name: str,
        node: type[Node],
        opener: str,
        closer: str | None = None,
        content: ContentMode = 'value',
        allow_opener_content: bool = False,
        strip_content: bool = False,
    ) -> None:
        self.node = node
        self.opener = opener
        self.closer = closer
        self.content = content
        self.allow_opener_content = allow_opener_content
        self.strip_content = strip_content
        self._opener_re = _opener_pattern(self)
        self._closer_re = _closer_pattern(self)
        self._node_factory = _fenced_node_factory(self)
        super().__init__(
            name=name,
            pattern=rf'[ \t]{{0,3}}{re.escape(opener)}',
        )

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        opener_content = _parse_opener_content(state.line, self, self._opener_re)
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
        if self.strip_content:
            value = value.strip()
        return self._node_factory(parser, state, value)


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


def _fenced_node_factory(syntax: BlockFenced) -> FencedNodeFactory:
    node_class = syntax.node
    if syntax.content == 'value':
        if not issubclass(node_class, LiteralNode):
            raise TypeError(f'{syntax.name!r} requires a Literal node for value content')
        node_factory = cast(Callable[..., Node], node_class)
        return lambda parser, state, value: node_factory(value=value)

    if syntax.content == 'children':
        if not issubclass(node_class, Parent):
            raise TypeError(f'{syntax.name!r} requires a Parent node for children content')
        node_factory = cast(Callable[..., Node], node_class)
        return lambda parser, state, value: node_factory(children=parser.parse_blocks(value, state))

    raise TypeError(f'{syntax.name!r} uses unsupported content mode {syntax.content!r}')
