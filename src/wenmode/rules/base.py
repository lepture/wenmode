from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, TypeAlias, cast

from wenmode.nodes import Node

from .._parser.state import BlockState
from .transforms import NodeTransform, RootTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser

Opener: TypeAlias = str | tuple[str, ...]


@dataclass(frozen=True, slots=True)
class InlineCandidate:
    """Candidate inline match produced by rule dispatch."""

    start: int
    match: re.Match[str] | None = None


class Rule:
    """Base class for parser rules.

    :param name: Stable rule name. Parser rule dictionaries are keyed by this
        value.
    """

    name: str
    order: ClassVar[int] = 100

    def __init__(self, name: str | None = None) -> None:
        self.name = cast(str, resolve_string_attribute(self, 'name', name))
        self.root_transforms: list[RootTransform] = []
        self.node_transforms: list[NodeTransform] = []


class BlockRule(Rule):
    """Base class for block-level Markdown rules.

    :param pattern: Regular expression pattern used to detect block openers.
    """

    pattern: str

    def __init__(self, name: str | None = None, pattern: str | None = None) -> None:
        super().__init__(name)
        self.pattern = cast(str, resolve_string_attribute(self, 'pattern', pattern))

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
        Set this to ``None`` for trigger-only rules that implement
        :meth:`parse` directly.
    :param opener: Optional single-character opener, or tuple of single-character
        openers, that can start the rule. Supplying openers lets the parser
        dispatch inline rules more efficiently; rule implementations remain
        responsible for checking any longer delimiter syntax.
    """

    pattern: str | None = None
    opener: Opener = ''
    openers: tuple[str, ...]
    compiled: re.Pattern[str]

    def __init__(self, name: str | None = None, pattern: str | None = None, opener: Opener | None = None) -> None:
        super().__init__(name)
        self.pattern = resolve_string_attribute(self, 'pattern', pattern, optional=True)
        self.opener = resolve_opener_attribute(self, opener)
        self.openers = normalize_openers(self.opener)
        self.compiled = re.compile(self.pattern if self.pattern is not None else r'(?!)')

    def search_candidate(self, text: str, pos: int = 0) -> InlineCandidate | None:
        if self.pattern is None:
            return None
        match = self.compiled.search(text, pos)
        if match is None:
            return None
        return InlineCandidate(match.start(), match)

    def match_candidate(self, text: str, start: int) -> InlineCandidate | None:
        if self.pattern is None:
            return InlineCandidate(start)
        match = self.compiled.match(text, start)
        if match is None:
            return None
        return InlineCandidate(start, match)

    def parse(
        self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
    ) -> tuple[Node | None, int]:
        """Parse an inline node from ``candidate``.

        :param parser: Active parser.
        :param text: Full inline source text.
        :param candidate: Candidate start and optional regex match from dispatch.
        :param state: Current block state.
        :returns: A ``(node, end_index)`` pair. Return ``(None,
            candidate.start)`` to decline the match.
        """
        raise NotImplementedError


def resolve_string_attribute(
    obj: object, name: str, value: str | None, default: str | None = None, *, optional: bool = False
) -> str | None:
    if value is None:
        resolved = getattr(type(obj), name, default)
    else:
        resolved = value
    if optional and resolved is None:
        return None
    if isinstance(resolved, str):
        return resolved
    requirement = 'string or None' if optional else 'string'
    raise TypeError(f'{type(obj).__name__} requires a {name} {requirement}')


def resolve_opener_attribute(obj: object, value: Opener | None) -> Opener:
    if value is None:
        resolved = getattr(type(obj), 'opener', '')
    else:
        resolved = value
    if isinstance(resolved, str):
        return resolved
    if isinstance(resolved, tuple) and all(isinstance(opener, str) for opener in resolved):
        return resolved
    raise TypeError(f'{type(obj).__name__} requires an opener string or tuple of strings')


def normalize_openers(opener: Opener) -> tuple[str, ...]:
    values: tuple[str, ...]
    if isinstance(opener, str):
        values = (opener,) if opener else ()
    else:
        values = opener

    normalized: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not value:
            raise ValueError('opener values must not be empty')
        if len(value) != 1:
            raise ValueError('opener values must be single characters')
        if value in seen:
            continue
        seen.add(value)
        normalized.append(value)
    return tuple(normalized)
