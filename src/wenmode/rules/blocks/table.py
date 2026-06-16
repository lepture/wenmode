from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node, TableCell, TableRow
from wenmode.nodes import Table as TableNode
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


DELIMITER_CELL_RE = re.compile(r'^:?-{3,}:?$')
CELL_SPACE_RE = re.compile(r'[ \t]+')


class Table(BlockRule):
    def __init__(self) -> None:
        super().__init__('table', r'[ \t]{0,3}.*\|.*(?:\r?\n)?$')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> TableNode | None:
        if not state.has(1):
            return None

        header_line = state.line.rstrip('\r\n')
        delimiter_line = state.peek(1).rstrip('\r\n')
        if not has_unescaped_pipe(header_line):
            return None

        header_cells = split_table_row(header_line)
        align = parse_delimiter_row(delimiter_line)
        if align is None or len(header_cells) != len(align):
            return None

        rows: list[Node] = [TableRow(children=parse_cells(parser, header_cells, state))]
        state.advance(2)

        while not state.done:
            line = state.line.rstrip('\r\n')
            if line.strip() == '' or not has_unescaped_pipe(line):
                break
            cells = normalize_row(split_table_row(line), len(align))
            rows.append(TableRow(children=parse_cells(parser, cells, state)))
            state.advance()

        return TableNode(children=rows, align=align)


def parse_cells(parser: Wenmode, cells: list[str], state: BlockState) -> list[Node]:
    return [TableCell(children=parser.parse_inlines(cell.strip(), state)) for cell in cells]


def parse_delimiter_row(line: str) -> list[str | None] | None:
    if not has_unescaped_pipe(line):
        return None

    align: list[str | None] = []
    for cell in split_table_row(line):
        value = CELL_SPACE_RE.sub('', cell)
        if DELIMITER_CELL_RE.fullmatch(value) is None:
            return None
        left = value.startswith(':')
        right = value.endswith(':')
        if left and right:
            align.append('center')
        elif left:
            align.append('left')
        elif right:
            align.append('right')
        else:
            align.append(None)
    return align


def normalize_row(cells: list[str], size: int) -> list[str]:
    if len(cells) < size:
        return cells + [''] * (size - len(cells))
    return cells[:size]


def split_table_row(line: str) -> list[str]:
    value = line.strip()
    if value.startswith('|'):
        value = value[1:]
    if value.endswith('|') and not is_escaped(value, len(value) - 1):
        value = value[:-1]

    cells: list[str] = []
    start = 0
    index = 0
    code_marker = ''
    while index < len(value):
        char = value[index]
        if char == '\\':
            index += 2
            continue
        if char == '`':
            marker_end = index
            while marker_end < len(value) and value[marker_end] == '`':
                marker_end += 1
            marker = value[index:marker_end]
            if code_marker == marker:
                code_marker = ''
            elif not code_marker:
                code_marker = marker
            index = marker_end
            continue
        if char == '|' and not code_marker:
            cells.append(value[start:index])
            start = index + 1
        index += 1

    cells.append(value[start:])
    return cells


def has_unescaped_pipe(line: str) -> bool:
    return any(char == '|' and not is_escaped(line, index) for index, char in enumerate(line))


def is_escaped(value: str, index: int) -> bool:
    backslashes = 0
    cursor = index - 1
    while cursor >= 0 and value[cursor] == '\\':
        backslashes += 1
        cursor -= 1
    return backslashes % 2 == 1
