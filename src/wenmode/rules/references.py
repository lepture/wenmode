from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.rules.base import BlockRule
from wenmode.state import Reference
from wenmode.utils import normalize_label, normalize_label_text, normalize_uri_text

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


REFERENCE_START_RE = re.compile(r'^[ \t]{0,3}\[(?P<label>(?:\\.|[^\[\]\\\n]){1,999})\]:[ \t]*(?P<rest>.*)$')
FENCE_RE = re.compile(r'^[ \t]{0,3}(`{3,}|~{3,})')


def extract_references(text: str, parser: Wenmode) -> tuple[str, dict[str, Reference]]:
    lines = text.splitlines(keepends=True)
    references: dict[str, Reference] = {}
    output: list[str] = []
    index = 0

    while index < len(lines):
        fence = FENCE_RE.match(lines[index]) if 'fenced_code' in parser.rules else None
        if fence is not None:
            fence_char = fence.group(1)[0]
            fence_size = len(fence.group(1))
            output.append(lines[index])
            index += 1
            while index < len(lines):
                output.append(lines[index])
                index += 1
                if re.match(
                    rf'^[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*$', output[-1].rstrip('\r\n')
                ):
                    break
            continue

        blockquote_reference = parse_blockquote_reference(lines[index]) if 'blockquote' in parser.rules else None
        if blockquote_reference is not None:
            label, reference = blockquote_reference
            references.setdefault(label, reference)
            output.append('>\n')
            index += 1
            continue

        multiline_label = parse_multiline_label_reference(lines, index)
        if multiline_label is not None:
            next_index, label, url, title = multiline_label
            references.setdefault(normalize_label(label), Reference(url=url, title=title))
            index = next_index
            continue

        if output and output[-1].strip() and not can_interrupt_after(parser, output[-1]):
            output.append(lines[index])
            index += 1
            continue

        parsed = parse_reference(lines, index)
        if parsed is None:
            output.append(lines[index])
            index += 1
            continue

        next_index, label, url, title = parsed
        references.setdefault(normalize_label(label), Reference(url=url, title=title))
        index = next_index

    return ''.join(output), references


def can_interrupt_after(parser: Wenmode, line: str) -> bool:
    stripped = line.lstrip(' \t')
    interrupt_rules = {'atx_heading', 'fenced_code', 'blockquote', 'list'}
    for name in interrupt_rules:
        rule = parser.rules.get(name)
        if isinstance(rule, BlockRule) and re.match(rule.pattern.replace(r'[ \t]{0,3}', ''), stripped):
            return True
    return False


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

    match = re.match(r'(?:\\.|[^\s()\\]|[(](?:\\.|[^()\s\\])*[)])+', text)
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


def parse_blockquote_reference(line: str) -> tuple[str, Reference] | None:
    match = re.match(r'^[ \t]{0,3}> ?(.*)$', line.rstrip('\r\n'))
    if match is None:
        return None
    parsed = parse_reference([match.group(1) + '\n'], 0)
    if parsed is None:
        return None
    _, label, url, title = parsed
    return normalize_label(label), Reference(url=url, title=title)


def parse_multiline_label_reference(lines: list[str], index: int) -> tuple[int, str, str, str | None] | None:
    if not re.match(r'^[ \t]{0,3}\[[^\]\n]*$', lines[index].rstrip('\r\n')):
        return None
    label_lines = [lines[index].strip()[1:]]
    cursor = index + 1
    while cursor < len(lines):
        line = lines[cursor].rstrip('\r\n')
        end = re.match(r'^(?P<label_end>[^\]]*)\]:[ \t]*(?P<rest>.*)$', line)
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
