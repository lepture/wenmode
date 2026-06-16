from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.rules.base import BlockRule
from wenmode.state import Reference
from wenmode.utils import normalize_label, normalize_label_text, normalize_uri_text

if TYPE_CHECKING:
    from wenmode.parser import Wenmode
    from wenmode.state import BlockState


REFERENCE_START_RE = re.compile(r'^[ \t]{0,3}\[(?P<label>(?:\\.|[^\[\]\\\n]){1,999})\]:[ \t]*(?P<rest>.*)$')
REFERENCE_DESTINATION_RE = re.compile(r'(?:\\.|[^\s()\\]|[(](?:\\.|[^()\s\\])*[)])+')
MULTILINE_LABEL_START_RE = re.compile(r'^[ \t]{0,3}\[[^\]\n]*$')
MULTILINE_LABEL_END_RE = re.compile(r'^(?P<label_end>[^\]]*)\]:[ \t]*(?P<rest>.*)$')


class ReferenceDefinition(BlockRule):
    def __init__(self) -> None:
        super().__init__('reference_definition', r'[ \t]{0,3}\[')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> None:
        multiline_label = parse_multiline_label_reference(state.lines, state.index)
        if multiline_label is not None:
            next_index, label, url, title = multiline_label
            state.references.setdefault(normalize_label(label), Reference(url=url, title=title))
            state.index = next_index
            return None

        parsed = parse_reference(state.lines, state.index)
        if parsed is None:
            return None

        next_index, label, url, title = parsed
        state.references.setdefault(normalize_label(label), Reference(url=url, title=title))
        state.index = next_index
        return None


def parse_reference(lines: list[str], index: int) -> tuple[int, str, str, str | None] | None:
    match = REFERENCE_START_RE.match(lines[index].rstrip('\r\n'))
    if match is None:
        return None

    label = normalize_label_text(match.group('label'))
    rest = match.group('rest')
    index += 1

    while rest == '' and index < len(lines):
        continuation = lines[index].rstrip('\r\n')
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
            parsed_title, index = parse_multiline_reference_title(remainder, lines, index)
        if parsed_title is None:
            return None
        title, remainder = parsed_title
        if remainder.strip():
            return None
    elif index < len(lines):
        next_line = lines[index].rstrip('\r\n')
        parsed_title = parse_reference_title(next_line.strip())
        if parsed_title is not None and not parsed_title[1].strip():
            title = parsed_title[0]
            index += 1

    return index, label, normalize_uri_text(destination), title


def parse_reference_destination(text: str) -> tuple[str | None, str]:
    text = text.lstrip()
    if text.startswith('<'):
        end = text.find('>')
        if end == -1:
            return None, text
        destination = text[1:end]
        if '\n' in destination:
            return None, text
        return destination, text[end + 1 :]

    match = REFERENCE_DESTINATION_RE.match(text)
    if match is None:
        return None, text
    return match.group(0), text[match.end() :]


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
    first_line: str, lines: list[str], index: int
) -> tuple[tuple[str, str] | None, int]:
    title_lines = [first_line]
    while index < len(lines):
        if lines[index].strip() == '':
            return None, index
        title_lines.append(lines[index].rstrip('\r\n'))
        index += 1
        parsed = parse_reference_title('\n'.join(title_lines))
        if parsed is not None:
            return parsed, index
    return None, index


def parse_multiline_label_reference(lines: list[str], index: int) -> tuple[int, str, str, str | None] | None:
    if not MULTILINE_LABEL_START_RE.match(lines[index].rstrip('\r\n')):
        return None
    label_lines = [lines[index].strip()[1:]]
    cursor = index + 1
    while cursor < len(lines):
        line = lines[cursor].rstrip('\r\n')
        end = MULTILINE_LABEL_END_RE.match(line)
        if end is not None:
            label_lines.append(end.group('label_end'))
            label = normalize_label_text('\n'.join(label_lines))
            if normalize_label(label) == '':
                return None
            destination, rest_after_destination = parse_reference_destination(end.group('rest'))
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
