from __future__ import annotations

import re
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.utils import normalize_label, normalize_label_text, normalize_uri_text
from wenmode.utils.text import parse_angle_destination, parse_bare_destination

from .._parser.store import StateKey
from .base import BlockCandidate, BlockRule, Rule
from .transforms import RootTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser

    from .._parser.state import BlockState


REFERENCE_START_RE = re.compile(r'^[ \t]{0,3}\[(?P<label>(?:\\.|[^\[\]\\\n]){1,999})\]:[ \t]*')
MULTILINE_LABEL_START_RE = re.compile(r'^[ \t]{0,3}\[[^\]\n]*$')
MULTILINE_LABEL_END_RE = re.compile(r'^(?P<label_end>[^\]]*)\]:[ \t]*')


@dataclass
class ReferenceState:
    url: str
    title: str | None = None


ReferenceCache = dict[str, ReferenceState]
REFERENCES_KEY = StateKey[ReferenceCache]('wenmode.references', lambda: {})


class ReferenceDefinition(BlockRule):
    """Parse link and image reference definitions.

    Markdown syntax:

    .. code-block:: markdown

       [label]: https://example.com "Title"
    """

    name = 'reference_definition'
    pattern = r'[ \t]{0,3}\[(?!\^)'

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> None:
        multiline_label = parse_multiline_label_reference(state, state.index)
        if multiline_label is not None:
            next_index, label, url, title = multiline_label
            state.store.get(REFERENCES_KEY).setdefault(normalize_label(label), ReferenceState(url=url, title=title))
            state.index = next_index
            return None

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
    required_rules: Sequence[type[Rule] | Rule] = [ReferenceDefinition]


def resolve_state_reference(state: BlockState, label: str) -> ReferenceState | None:
    return state.store.get(REFERENCES_KEY).get(normalize_label(label))


def parse_reference(state: BlockState, index: int) -> tuple[int, str, str, str | None] | None:
    line = state.line_at(index).rstrip('\r\n')
    match = REFERENCE_START_RE.match(line)
    if match is None:
        return None

    label = normalize_label_text(match.group('label'))
    if label.startswith('^'):
        return None
    rest = line[match.end() :]
    index += 1

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
            elif char == closer:
                title = ''.join(title_parts[:-1])
                return (normalize_label_text(title), line[position + 1 :]), index

        if not state.has_index(index):
            return None, index

        line = state.line_at(index).rstrip('\r\n')
        if line.strip() == '':
            return None, index

        title_parts.append('\n')
        if escaped:
            escaped = False
        start = 0
        index += 1


def parse_multiline_label_reference(state: BlockState, index: int) -> tuple[int, str, str, str | None] | None:
    if not MULTILINE_LABEL_START_RE.match(state.line_at(index).rstrip('\r\n')):
        return None
    label_lines = [state.line_at(index).strip()[1:]]
    cursor = index + 1
    while state.has_index(cursor):
        line = state.line_at(cursor).rstrip('\r\n')
        end = MULTILINE_LABEL_END_RE.match(line)
        if end is not None:
            label_lines.append(end.group('label_end'))
            label = normalize_label_text('\n'.join(label_lines))
            if label.startswith('^') or normalize_label(label) == '':
                return None
            destination, rest_after_destination = parse_reference_destination(line[end.end() :])
            if destination is None:
                return None
            title: str | None = None
            remainder = rest_after_destination.strip()
            if remainder:
                parsed_title = parse_reference_title(remainder)
                if parsed_title is None:
                    return None
                title, remainder = parsed_title
                if remainder.strip():
                    return None
            return cursor + 1, label, normalize_uri_text(destination), title
        if line.strip() == '':
            return None
        label_lines.append(line)
        cursor += 1
    return None
