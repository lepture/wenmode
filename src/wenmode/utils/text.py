from __future__ import annotations

import html
import re
import string
from html.entities import html5
from urllib.parse import quote

ESCAPABLE = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'
ESCAPABLE_CHARS = set(string.punctuation)
BACKSLASH_ESCAPE_RE = re.compile(rf'\\([{ESCAPABLE}])')
WHITESPACE_RE = re.compile(r'\s+')
CHARACTER_REFERENCE_RE = re.compile(r'&(?:#[xX][0-9A-Fa-f]+|#\d+|[A-Za-z][A-Za-z0-9]{1,31});')
BARE_DESTINATION_FAST_RE = re.compile(r'[^ \t\r\n()\\]+')


def normalize_label_text(value: str) -> str:
    value = BACKSLASH_ESCAPE_RE.sub(r'\1', value)
    return decode_character_references(value)


def normalize_label(value: str) -> str:
    return WHITESPACE_RE.sub(' ', normalize_label_text(value).strip()).casefold()


def normalize_uri_text(value: str) -> str:
    return quote(normalize_label_text(value), safe="/:?#@!$&'()*+,;=%._~-")


def parse_angle_destination(text: str, start: int) -> tuple[str | None, int]:
    chars: list[str] = []
    index = start + 1
    while index < len(text):
        char = text[index]
        if char == '\\' and index + 1 < len(text) and text[index + 1] in ESCAPABLE_CHARS:
            chars.append(text[index : index + 2])
            index += 2
            continue
        if char == '>':
            return ''.join(chars), index + 1
        if char in '<\n\r\x00':
            return None, start
        chars.append(char)
        index += 1
    return None, start


def parse_bare_destination(text: str, start: int) -> tuple[str | None, int]:
    destination, end, _failure_end = parse_bare_destination_result(text, start)
    return destination, end


def parse_bare_destination_result(text: str, start: int) -> tuple[str | None, int, int | None]:
    match = BARE_DESTINATION_FAST_RE.match(text, start)
    if match is not None:
        end = match.end()
        if end >= len(text) or text[end] not in '(\\':
            return match.group(0), end, None

    chars: list[str] = []
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char in ' \t\r\n':
            break
        if char == '\\' and index + 1 < len(text) and text[index + 1] in ESCAPABLE_CHARS:
            chars.append(text[index : index + 2])
            index += 2
            continue
        if char == '(':
            depth += 1
        elif char == ')':
            if depth == 0:
                break
            depth -= 1
        chars.append(char)
        index += 1

    if depth:
        return None, start, index
    return ''.join(chars), index, None


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


def is_escaped(text: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and text[cursor] == '\\':
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1


def unquote_attribute_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].replace('\\' + value[0], value[0]).replace('\\\\', '\\')
    return value
