from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal, TypeAlias

from wenmode.nodes import Node

ContentMode: TypeAlias = Literal['children', 'value']
RendererFallbackMode: TypeAlias = Literal['children', 'value']


@dataclass(frozen=True)
class BlockFenced:
    """Declarative block rule for literal fenced blocks."""

    name: str
    node: type[Node]
    opener: str
    closer: str | None = None
    content: ContentMode = 'value'
    allow_opener_content: bool = False
    strip_content: bool = False


@dataclass(frozen=True)
class InlineDelimited:
    """Declarative inline rule for paired literal delimiters."""

    name: str
    node: type[Node]
    opener: str
    closer: str
    content: ContentMode = 'children'
    trigger_chars: str | None = None
    allow_newline: bool = True
    reject_empty: bool = True
    reject_opening_whitespace: bool = True
    reject_closing_whitespace: bool = True
    reject_longer_run: bool = True
    strip_content: bool = False
    escape: bool = True


@dataclass(frozen=True)
class InlineLiteral:
    """Declarative inline rule for paired delimiters that produce literal nodes."""

    name: str
    node: type[Node]
    opener: str
    closer: str
    trigger_chars: str | None = None
    allow_newline: bool = False
    reject_empty: bool = True
    reject_opening_whitespace: bool = True
    reject_closing_whitespace: bool = True
    reject_closing_before_digit: bool = False
    reject_longer_run: bool = False
    reject_adjacent_delimiter: bool = False
    strip_content: bool = False
    escape: bool = True


@dataclass(frozen=True)
class RenderTemplate:
    """Declarative renderer template.

    Templates may use ``{children}`` for rendered child nodes and ``{value}``
    for literal node values.
    """

    template: str


@dataclass(frozen=True)
class RendererFallback:
    """Declarative renderer fallback for wrapper-free node rendering."""

    mode: RendererFallbackMode


SyntaxSpec: TypeAlias = BlockFenced | InlineDelimited | InlineLiteral
RendererSpec: TypeAlias = RenderTemplate | RendererFallback


@dataclass(frozen=True)
class DeclarativePluginSpec:
    """Declarative plugin specification installable by ``install_declarative``."""

    name: str
    syntax: list[SyntaxSpec]
    renderers: Mapping[str, Mapping[str, RendererSpec]]
