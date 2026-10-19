from __future__ import annotations

import re
from bisect import bisect_left
from typing import TYPE_CHECKING

from wenmode.nodes import InlineCode as InlineCodeNode
from wenmode.nodes import Node, Text

from ..._parser.rule_base import InlineCandidate, InlineRule
from ..._parser.state import BlockState
from ..._parser.store import StateKey

if TYPE_CHECKING:
    from wenmode.parser import Parser


CODE_LINE_ENDING_RE = re.compile(r'\r\n?|\n')
BACKTICK_RUN_RE = re.compile(r'`+')
BacktickRuns = dict[int, list[int]]
BacktickCache = dict[int, tuple[str, BacktickRuns]]
BACKTICK_RUNS = StateKey[BacktickCache]('wenmode.inline.backticks', lambda: {})


class InlineCode(InlineRule):
    """Parse inline code spans.

    Markdown syntax:

    .. code-block:: markdown

       `code`
    """

    name = 'inline_code'
    opener = '`'

    def match_candidate(self, text: str, start: int) -> InlineCandidate | None:
        if text[start] != '`' or (start > 0 and text[start - 1] == '`'):
            return None
        match = BACKTICK_RUN_RE.match(text, start)
        if match is None:
            return None
        return InlineCandidate(start, match)

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        start = candidate.start
        match = candidate.match
        assert match is not None
        marker_length = match.end() - start
        value_start = match.end()
        end = find_matching_backtick_run(text, value_start, marker_length, state.store.get(BACKTICK_RUNS))
        if end is None:
            return Text(value=text[start:value_start]), value_start
        value = CODE_LINE_ENDING_RE.sub(' ', text[value_start:end])
        if len(value) >= 2 and value.startswith(' ') and value.endswith(' ') and any(char != ' ' for char in value):
            value = value[1:-1]
        return InlineCodeNode(value=value), end + marker_length


def find_matching_backtick_run(
    text: str, start: int, marker_length: int, cache: BacktickCache | None = None
) -> int | None:
    """Scan successful spans once; index the source only after the first failure.

    Successful spans consume their entire search range. A failed search builds
    an exact-length index so later unmatched openers cannot rescan that suffix.
    Backslashes within code are literal, so escaped runs also appear in the index.
    """
    # No source has a failure index until the first unmatched run.
    cached = cache.get(id(text)) if cache else None
    if cached is not None and cached[0] is text:
        positions = cached[1].get(marker_length)
        if not positions:
            return None
        index = bisect_left(positions, start)
        return positions[index] if index < len(positions) else None

    for run in BACKTICK_RUN_RE.finditer(text, start):
        if run.end() - run.start() == marker_length:
            return run.start()
    if cache is not None:
        runs: BacktickRuns = {}
        for run in BACKTICK_RUN_RE.finditer(text):
            runs.setdefault(run.end() - run.start(), []).append(run.start())
        cache[id(text)] = (text, runs)
    return None
