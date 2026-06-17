from __future__ import annotations

import re

NAME_RE = re.compile(r'[A-Za-z][A-Za-z0-9_-]*')


def parse_directive_head(text: str, start: int = 0) -> tuple[str, str | None, dict[str, str] | None, int] | None:
    match = NAME_RE.match(text, start)
    if match is None:
        return None

    name = match.group(0)
    index = match.end()
    label: str | None = None
    attributes: dict[str, str] | None = None

    if index < len(text) and text[index] == '[':
        end = find_balanced(text, index, '[', ']')
        if end is None:
            return None
        label = text[index + 1 : end]
        index = end + 1

    if index < len(text) and text[index] == '{':
        end = find_balanced(text, index, '{', '}')
        if end is None:
            return None
        attributes = parse_attributes(text[index + 1 : end])
        index = end + 1

    return name, label, attributes, index


def find_balanced(text: str, start: int, opener: str, closer: str) -> int | None:
    depth = 0
    index = start
    while index < len(text):
        char = text[index]
        if char == '\\':
            index += 2
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                return index
        index += 1
    return None


def parse_attributes(text: str) -> dict[str, str]:
    attributes: dict[str, str] = {}
    classes: list[str] = []

    for token in tokenize_attributes(text):
        if token.startswith('#') or token.startswith('.'):
            parse_shortcuts(token, attributes, classes)
            continue

        if '=' in token:
            key, value = token.split('=', 1)
            key = key.strip()
            if key:
                attributes[key] = unquote_attribute_value(value.strip())
            continue

        key = token.strip()
        if key:
            attributes[key] = ''

    if classes:
        attributes['class'] = ' '.join(value for value in classes if value)
    return attributes


def tokenize_attributes(text: str) -> list[str]:
    tokens: list[str] = []
    current: list[str] = []
    quote = ''
    escaped = False

    for char in text:
        if escaped:
            current.append(char)
            escaped = False
            continue
        if char == '\\':
            current.append(char)
            escaped = True
            continue
        if quote:
            current.append(char)
            if char == quote:
                quote = ''
            continue
        if char in {'"', "'"}:
            current.append(char)
            quote = char
            continue
        if char.isspace():
            if current:
                tokens.append(''.join(current))
                current.clear()
            continue
        current.append(char)

    if current:
        tokens.append(''.join(current))
    return tokens


def parse_shortcuts(token: str, attributes: dict[str, str], classes: list[str]) -> None:
    index = 0
    while index < len(token):
        marker = token[index]
        if marker not in {'#', '.'}:
            break
        index += 1
        start = index
        while index < len(token) and token[index] not in {'#', '.'}:
            index += 1
        value = token[start:index]
        if not value:
            continue
        if marker == '#':
            attributes['id'] = value
        else:
            classes.append(value)


def unquote_attribute_value(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1].replace('\\' + value[0], value[0]).replace('\\\\', '\\')
    return value
