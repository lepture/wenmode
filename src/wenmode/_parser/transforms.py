from __future__ import annotations

from typing import TYPE_CHECKING

from .store import StateKey

if TYPE_CHECKING:
    from wenmode.nodes import Node, Root
    from wenmode.parser import Parser

    from .state import BlockState

NODE_TRANSFORM_FINALIZATION = StateKey[bool]('wenmode.node_transform.finalization', lambda: False)

class RootTransform:
    """Base class for document-wide transforms attached by rules.

    Root transforms can collect definitions, defer inline parsing, and update
    the parsed root after block parsing completes.
    """

    name: str
    defer_inlines = False

    def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
        """Prepare document-wide state before deferred inlines resolve."""
        pass

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        """Update the root after deferred inlines have resolved."""
        pass


class NodeTransform:
    """Base class for per-node transforms attached by parser rules.

    Node transforms run immediately after the owning block or continuation rule
    returns a node. Their per-node work does not require a complete root and can
    run during incremental parsing. They mutate the supplied node in place;
    they do not replace it. An optional ``finalize`` hook runs only after
    full-document parsing completes.
    """

    name: str
    defer_inlines = False

    def transform(self, parser: Parser, node: Node, state: BlockState) -> None:
        """Mutate the supplied node in place."""
        pass

    def finalize(self, parser: Parser, root: Root, state: BlockState) -> None:
        """Finalize transformed nodes after a full-document parse.

        Incremental parsing does not call this hook: nodes may already have
        been yielded before later document content is known.
        """
        pass
