from __future__ import annotations


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
