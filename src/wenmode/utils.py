from __future__ import annotations

import html
import re
from collections.abc import Sequence
from html.entities import html5
from urllib.parse import quote

ESCAPABLE = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'
BACKSLASH_ESCAPE_RE = re.compile(rf'\\([{ESCAPABLE}])')
WHITESPACE_RE = re.compile(r'\s+')
CHARACTER_REFERENCE_RE = re.compile(r'&(?:#[xX][0-9A-Fa-f]+|#[0-9]+|[A-Za-z][A-Za-z0-9]{1,31});')


def normalize_label_text(value: str) -> str:
    value = BACKSLASH_ESCAPE_RE.sub(r'\1', value)
    return decode_character_references(value)


def normalize_label(value: str) -> str:
    return WHITESPACE_RE.sub(' ', normalize_label_text(value).strip()).casefold()


def normalize_uri_text(value: str) -> str:
    return quote(normalize_label_text(value), safe="/:?#@!$&'()*+,;=%._~-")


def decode_character_references(value: str) -> str:
    """Decode Markdown character references without accepting legacy no-semicolon names."""

    def replace(match: re.Match[str]) -> str:
        raw = match.group(0)
        if raw.startswith(('&#x', '&#X')):
            codepoint = int(raw[3:-1], 16)
            return character_reference_from_codepoint(codepoint, raw)
        if raw.startswith('&#'):
            codepoint = int(raw[2:-1], 10)
            return character_reference_from_codepoint(codepoint, raw)
        if raw[1:] not in html5:
            return raw
        return html.unescape(raw)

    return CHARACTER_REFERENCE_RE.sub(replace, value)


def character_reference_from_codepoint(codepoint: int, raw: str) -> str:
    if codepoint == 0:
        return '\ufffd'
    if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
        return raw
    return html.unescape(raw)


def expand_leading_tabs(line: str, start_column: int = 0) -> str:
    column = start_column
    parts: list[str] = []
    index = 0
    while index < len(line):
        char = line[index]
        if char == ' ':
            parts.append(' ')
            column += 1
        elif char == '\t':
            size = 4 - column % 4
            parts.append(' ' * size)
            column += size
        else:
            break
        index += 1
    return ''.join(parts) + line[index:]


def count_indent(text: str) -> int:
    return count_indent_from(text, 0)


def count_indent_from(text: str, start_column: int) -> int:
    column = start_column
    for char in text:
        if char == ' ':
            column += 1
        elif char == '\t':
            column += 4 - column % 4
        else:
            break
    return column


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == '\\':
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def compile_disallowed_html_filter(tags: Sequence[str]) -> re.Pattern[str] | None:
    if not tags:
        return None
    tag_pattern = '|'.join(re.escape(tag) for tag in tags)
    return re.compile(rf'(?i)<(?=/?(?:{tag_pattern})(?:\s|/?>|$))')


def filter_disallowed_html(value: str, pattern: re.Pattern[str] | None) -> str:
    if pattern is None:
        return value
    return pattern.sub('&lt;', value)


def match_pattern(pattern: re.Pattern[str], line: str) -> bool:
    return pattern.match(line) is not None
