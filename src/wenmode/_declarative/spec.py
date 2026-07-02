from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from wenmode.nodes import Node

ContentMode = Literal['children', 'value']


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
class RenderTemplate:
    """Declarative renderer template.

    Templates may use ``{children}`` for rendered child nodes and ``{value}``
    for literal node values.
    """

    template: str


@dataclass(frozen=True)
class DeclarativePluginSpec:
    """Declarative plugin specification installable by ``install_declarative``."""

    name: str
    nodes: list[type[Node]]
    syntax: list[InlineDelimited]
    renderers: Mapping[str, Mapping[str, RenderTemplate]]
