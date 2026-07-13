from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wenmode.nodes import Node, Root
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


class NodeTransform:
    """Base class for per-node transforms attached by parser rules.

    Node transforms run immediately after the owning block or continuation rule
    returns a node. Unlike root transforms, they do not require a complete root
    and can run during incremental parsing. They mutate the supplied node in
    place; they do not replace it.
    """

    name: str
    defer_inlines = False

    def transform(self, parser: Parser, node: Node, state: BlockState) -> None:
        """Mutate the supplied node in place."""
        pass
