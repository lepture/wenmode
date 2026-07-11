from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wenmode.nodes import Root
    from wenmode.parser import Parser

    from .._parser.state import BlockState
    from .base import Rule


class RootTransform:
    """Base class for document-wide transforms attached by rules.

    Root transforms can collect definitions, request helper rules, defer inline
    parsing, and update the parsed root after block parsing completes.
    """

    name: str
    defer_inlines = False
    required_rules: Sequence[type[Rule] | Rule] = ()

    def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
        """Prepare document-wide state before deferred inlines resolve."""
        pass

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        """Update the root after deferred inlines have resolved."""
        pass
