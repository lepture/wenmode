from __future__ import annotations

import html
import re
from collections.abc import Sequence
from urllib.parse import quote

ESCAPABLE = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'


def normalize_label_text(value: str) -> str:
    value = re.sub(rf'\\([{ESCAPABLE}])', r'\1', value)
    return html.unescape(value)


def normalize_label(value: str) -> str:
    return re.sub(r'\s+', ' ', normalize_label_text(value).strip()).casefold()


def normalize_uri_text(value: str) -> str:
    return quote(normalize_label_text(value), safe="/:?#@!$&'()*+,;=%._~-")


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


def filter_disallowed_html(value: str, tags: Sequence[str]) -> str:
    if not tags:
        return value
    tag_pattern = '|'.join(re.escape(tag) for tag in tags)
    return re.sub(rf'(?i)<(?=/?(?:{tag_pattern})(?:\s|/?>|$))', '&lt;', value)
