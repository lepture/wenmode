from __future__ import annotations

import re
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import Node

from .._parser.state import BlockState
from .transforms import RootTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser


class Rule:
    """Base class for parser rules.

    :param name: Stable rule name. Parser rule dictionaries are keyed by this
        value.
    """

    name: str
    order: ClassVar[int] = 100

    def __init__(self, name: str | None = None) -> None:
        self.name = resolve_string_attribute(self, 'name', name)
        self.root_transforms: list[RootTransform] = []


class BlockRule(Rule):
    """Base class for block-level Markdown rules.

    :param pattern: Regular expression pattern used to detect block openers.
    """

    pattern: str

    def __init__(self, name: str | None = None, pattern: str | None = None) -> None:
        super().__init__(name)
        self.pattern = resolve_string_attribute(self, 'pattern', pattern)

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        """Parse a matched block opener.

        Implementations must advance ``state`` when they consume input. Returning
        a node without advancing state raises :exc:`RuntimeError`.

        :param parser: Active parser.
        :param state: Current block state.
        :param match: Match object from the compiled block opener.
        :returns: Parsed node, or ``None`` if the rule declines the match.
        """
        raise NotImplementedError


class ContinueRule(Rule):
    """Base class for rules that transform paragraph continuations."""

    def matches(self, line: str) -> bool:
        """Return whether a line should be checked by this continuation rule."""
        raise NotImplementedError

    def parse_paragraph_continuation(self, parser: Parser, state: BlockState, lines: list[str]) -> Node | None:
        """Parse a paragraph continuation.

        Returning ``None`` declines the continuation and must leave ``state``
        unchanged. Returning a replacement node requires advancing ``state``.
        Mutating ``state`` while declining, or returning a node without
        advancing state, raises :exc:`RuntimeError`.

        :param parser: Active parser.
        :param state: Current block state positioned at the continuation line.
        :param lines: Paragraph lines collected so far.
        :returns: Replacement node, or ``None`` to keep parsing the paragraph.
        """
        raise NotImplementedError


class InlineRule(Rule):
    """Base class for inline Markdown rules.

    :param pattern: Regular expression pattern used by this inline rule.
    :param trigger_chars: Optional literal characters that can start the rule.
        Supplying trigger characters lets the parser dispatch inline rules more
        efficiently.
    """

    pattern: str
    trigger_chars: str = ''
    compiled: re.Pattern[str]

    def __init__(self, name: str | None = None, pattern: str | None = None, trigger_chars: str | None = None) -> None:
        super().__init__(name)
        self.pattern = resolve_string_attribute(self, 'pattern', pattern)
        self.trigger_chars = resolve_string_attribute(self, 'trigger_chars', trigger_chars, default='')
        self.compiled = re.compile(self.pattern)

    def search(self, text: str, pos: int = 0) -> re.Match[str] | None:
        """Search for the next candidate match.

        Override this method for rules that need custom scanning behavior.
        """
        return self.compiled.search(text, pos)

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        """Parse a matched inline opener.

        :param parser: Active parser.
        :param text: Full inline source text.
        :param match: Match object returned by this rule.
        :param state: Current block state.
        :returns: A ``(node, end_index)`` pair. Return ``(None, match.start())``
            to decline the match.
        """
        raise NotImplementedError


def resolve_string_attribute(obj: object, name: str, value: str | None, default: str | None = None) -> str:
    if value is None:
        resolved = getattr(type(obj), name, default)
    else:
        resolved = value
    if isinstance(resolved, str):
        return resolved
    raise TypeError(f'{type(obj).__name__} requires a {name} string')
