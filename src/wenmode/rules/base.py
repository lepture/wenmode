from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import Node
from wenmode.state import BlockState

from .transforms import RootTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser


@dataclass
class Rule:
    """Base class for parser rules.

    :param name: Stable rule name. Parser rule dictionaries are keyed by this
        value.
    """

    name: str
    order: ClassVar[int] = 100
    root_transforms: list[RootTransform] = field(init=False, default_factory=list)


@dataclass
class BlockRule(Rule):
    """Base class for block-level Markdown rules.

    :param pattern: Regular expression pattern used to detect block openers.
    """

    pattern: str

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        """Parse a matched block opener.

        Implementations must advance ``state`` when they consume input.

        :param parser: Active parser.
        :param state: Current block state.
        :param match: Match object from the compiled block opener.
        :returns: Parsed node, or ``None`` if the rule declines the match.
        """
        raise NotImplementedError


@dataclass
class ContinueRule(Rule):
    """Base class for rules that transform paragraph continuations."""

    def matches(self, line: str) -> bool:
        """Return whether a line should be checked by this continuation rule."""
        return True

    def parse_paragraph_continuation(self, parser: Parser, state: BlockState, lines: list[str]) -> Node | None:
        """Parse a paragraph continuation.

        :param parser: Active parser.
        :param state: Current block state positioned at the continuation line.
        :param lines: Paragraph lines collected so far.
        :returns: Replacement node, or ``None`` to keep parsing the paragraph.
        """
        raise NotImplementedError


@dataclass
class InlineRule(Rule):
    """Base class for inline Markdown rules.

    :param pattern: Regular expression pattern used by this inline rule.
    :param trigger_chars: Optional literal characters that can start the rule.
        Supplying trigger characters lets the parser dispatch inline rules more
        efficiently.
    """

    pattern: str
    trigger_chars: str = ''
    compiled: re.Pattern[str] = field(init=False)

    def __post_init__(self) -> None:
        self.compiled = re.compile(self.pattern)

    def search(self, text: str, pos: int = 0) -> re.Match[str] | None:
        """Search for the next candidate match.

        Override this method for rules that need custom scanning behavior.
        """
        return self.compiled.search(text, pos)

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        """Parse a matched inline opener.

        :param parser: Active parser.
        :param text: Full inline source text.
        :param match: Match object returned by this rule.
        :param state: Current block state, if available.
        :returns: A ``(node, end_index)`` pair. Return ``(None, match.start())``
            to decline the match.
        """
        raise NotImplementedError
