from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from wenmode.nodes import Root
    from wenmode.parser import Parser
    from wenmode.state import BlockState

    from .base import Rule


class RootTransform(Protocol):
    name: str
    defer_inlines: bool
    required_rules: Sequence[type[Rule] | Rule]

    def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
        pass

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        pass
