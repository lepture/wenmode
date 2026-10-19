from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from wenmode.utils import normalize_label, normalize_label_text, normalize_uri_text
from wenmode.utils.text import parse_angle_destination, parse_bare_destination

from .._parser.rule_base import BlockCandidate, BlockRule
from .._parser.store import StateKey
from .._parser.transforms import RootTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser

    from .._parser.state import BlockState


@dataclass
class ReferenceState:
    url: str
    title: str | None = None


ReferenceCache = dict[str, ReferenceState]
REFERENCES_KEY = StateKey[ReferenceCache]('wenmode.references', lambda: {})


@dataclass
class ReferenceTitleScanCache:
    """Retain source identity and delimiter-specific failed line ranges."""

    source: list[str]
    failures: dict[str, tuple[int, int]] = field(default_factory=dict)


REFERENCE_TITLE_SCANS = StateKey[dict[int, ReferenceTitleScanCache]]('wenmode.reference.title_scans', lambda: {})


class ReferenceDefinition(BlockRule):
    """Parse link and image reference definitions.

    Markdown syntax:

    .. code-block:: markdown

       [label]: https://example.com "Title"
    """

    name = 'reference_definition'
    pattern = r'[ \t]{0,3}\[(?!\^)'

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> None:
        parsed = parse_reference(state, state.index)
        if parsed is None:
            return None

        next_index, label, url, title = parsed
        state.store.get(REFERENCES_KEY).setdefault(normalize_label(label), ReferenceState(url=url, title=title))
        state.index = next_index
        return None


class ReferenceTransform(RootTransform):
    name = 'reference'
    defer_inlines = True


def resolve_state_reference(state: BlockState, label: str) -> ReferenceState | None:
    return state.store.get(REFERENCES_KEY).get(normalize_label(label))


def parse_reference(state: BlockState, index: int) -> tuple[int, str, str, str | None] | None:
    parsed_label = parse_reference_label(state, index)
    if parsed_label is None:
        return None
    label, rest, index = parsed_label
    label = normalize_label_text(label)
    if label.startswith('^') or not normalize_label(label):
        return None

    while rest == '' and state.has_index(index):
        continuation = state.line_at(index).rstrip('\r\n')
        if continuation.strip() == '':
            return None
        rest = continuation.strip()
        index += 1

    destination, rest_after_destination = parse_reference_destination(rest)
    if destination is None:
        return None

    title: str | None = None
    if rest_after_destination and not rest_after_destination[0].isspace():
        return None
    remainder = rest_after_destination.strip()
    if remainder:
        parsed_title = parse_reference_title(remainder)
        if parsed_title is None and remainder[0] in '"\'(':
            parsed_title, index = parse_multiline_reference_title(remainder, state, index)
        if parsed_title is None:
            return None
        title, remainder = parsed_title
        if remainder.strip():
            return None
    elif state.has_index(index):
        next_line = state.line_at(index).rstrip('\r\n')
        parsed_title = parse_reference_title(next_line.strip())
        if parsed_title is not None and not parsed_title[1].strip():
            title = parsed_title[0]
            index += 1

    return index, label, normalize_uri_text(destination), title


def parse_reference_destination(text: str) -> tuple[str | None, str]:
    text = text.lstrip()
    if text.startswith('<'):
        destination, end = parse_angle_destination(text, 0)
        if destination is None:
            return None, text
        return destination, text[end:]

    destination, end = parse_bare_destination(text, 0)
    if destination is None or end == 0:
        return None, text
    return destination, text[end:]


def parse_reference_title(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    opener = text[0]
    closer = {'"': '"', "'": "'", '(': ')'}.get(opener)
    if closer is None:
        return None
    index = 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif opener == '(' and char == '(':
            return None
        elif char == closer:
            return normalize_label_text(text[1:index]), text[index + 1 :]
        index += 1
    return None


def parse_multiline_reference_title(
    first_line: str, state: BlockState, index: int
) -> tuple[tuple[str, str] | None, int]:
    opener = first_line[0]
    closer = {'"': '"', "'": "'", '(': ')'}.get(opener)
    if closer is None:
        return None, index

    scans = state.store.get(REFERENCE_TITLE_SCANS)
    cache = scans.get(id(state.lines))
    if cache is None:
        cache = ReferenceTitleScanCache(state.lines)
        scans[id(state.lines)] = cache
    scan_start = index

    title_parts: list[str] = []
    escaped = False
    line = first_line
    start = 1

    while True:
        for position in range(start, len(line)):
            char = line[position]
            title_parts.append(char)
            if escaped:
                escaped = False
            elif char == '\\':
                escaped = True
            elif opener == '(' and char == '(':
                return None, index
            elif char == closer:
                title = ''.join(title_parts[:-1])
                return (normalize_label_text(title), line[position + 1 :]), index

        # Escaping resets at each continuation line, so a failed suffix can be
        # reused regardless of the preceding title opener or trailing backslash.
        failed_range = cache.failures.get(closer)
        if failed_range is not None and failed_range[0] <= index < failed_range[1]:
            return None, failed_range[1]

        if not state.has_index(index):
            cache.failures[closer] = (scan_start, index)
            return None, index

        line = state.line_at(index).rstrip('\r\n')
        if line.strip() == '':
            cache.failures[closer] = (scan_start, index)
            return None, index

        title_parts.append('\n')
        if escaped:
            escaped = False
        start = 0
        index += 1


def parse_reference_label(state: BlockState, index: int) -> tuple[str, str, int] | None:
    """Read at most 999 source characters, stopping at the first unescaped bracket."""
    line = state.line_at(index).replace('\r\n', '\n').replace('\r', '\n')
    start = len(line) - len(line.lstrip(' \t'))
    if start > 3 or not line.startswith('[', start):
        return None
    parts: list[str] = []
    length = 0
    position = start + 1
    escaped = False
    while True:
        while position < len(line):
            char = line[position]
            if not escaped:
                if char == '[':
                    return None
                if char == ']':
                    if position + 1 < len(line) and line[position + 1] == ':' and length:
                        return ''.join(parts), line[position + 2 :].rstrip('\r\n').lstrip(' \t'), index + 1
                    return None
            length += 1
            if length > 999:
                return None
            parts.append(char)
            escaped = char == '\\' and not escaped
            position += 1
        index += 1
        if not state.has_index(index):
            return None
        line = state.line_at(index).replace('\r\n', '\n').replace('\r', '\n')
        if not line.strip():
            return None
        position = 0
        escaped = False
