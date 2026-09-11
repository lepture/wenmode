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


def count_indent_from(text: str, start_column: int = 0) -> int:
    column = start_column
    for char in text:
        if char == ' ':
            column += 1
        elif char == '\t':
            column += 4 - column % 4
        else:
            break
    return column


def count_indent_width(line: str, columns: int) -> tuple[int, int]:
    width = 0
    index = 0
    while index < len(line) and width < columns:
        char = line[index]
        if char == ' ':
            width += 1
        elif char == '\t':
            width += 4 - width % 4
        else:
            break
        index += 1
    return width, index


def indent_block(value: str, prefix: str) -> str:
    lines: list[str] = []
    for line in value.splitlines():
        if line:
            lines.append(prefix + line)
        else:
            lines.append('')
    return '\n'.join(lines)
