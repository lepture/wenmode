from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node, TableCell, TableRow
from wenmode.nodes import Table as TableNode
from wenmode.state import BlockState
from wenmode.utils import is_escaped

from ..base import BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


DELIMITER_CELL_RE = re.compile(r'^:?-+:?$')
CellSpan = tuple[str, int, int]


class Table(BlockRule):
    """Parse GFM pipe tables.

    Markdown syntax:

    .. code-block:: markdown

       | A | B |
       | --- | --- |
       | x | y |
    """

    def __init__(self, require_body_pipe: bool = True) -> None:
        super().__init__('table', r'[ \t]{0,3}.*\|.*(?:\r?\n)?$')
        self.require_body_pipe = require_body_pipe

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> TableNode | None:
        if not state.has(1):
            return None

        header_line = state.line.rstrip('\r\n')
        delimiter_line = state.peek(1).rstrip('\r\n')
        if not has_unescaped_pipe(header_line):
            return None

        header_cells = split_table_row_spans(header_line)
        align = parse_delimiter_row(delimiter_line)
        if align is None or len(header_cells) != len(align):
            return None

        header = TableRow(children=parse_cells(parser, header_cells, state, state.index))
        header.position = state.source.position_between(state.index, state.index + 1)
        rows: list[Node] = [header]
        state.advance(2)

        while not state.done:
            line = state.line.rstrip('\r\n')
            if (
                line.strip() == ''
                or parser.is_paragraph_interrupt(line, state)
                or (self.require_body_pipe and not has_unescaped_pipe(line))
            ):
                break
            row_index = state.index
            cells = normalize_row(split_table_row_spans(line), len(align), len(line))
            row = TableRow(children=parse_cells(parser, cells, state, row_index))
            row.position = state.source.position_between(row_index, row_index + 1)
            rows.append(row)
            state.advance()

        return TableNode(children=rows, align=align)


def parse_cells(parser: Parser, cells: list[CellSpan], state: BlockState, line_index: int) -> list[Node]:
    parsed: list[Node] = []
    for raw, start, end in cells:
        stripped = raw.strip()
        leading = len(raw) - len(raw.lstrip())
        text = unescape_table_pipes(stripped)
        cell = TableCell(
            children=parser.parse_inlines(text, state, source=state.source.line_text(line_index, start + leading, text))
        )
        cell.position = state.source.line_position(line_index, start, end)
        parsed.append(cell)
    return parsed


def parse_delimiter_row(line: str) -> list[str | None] | None:
    align: list[str | None] = []
    for cell, _, _ in split_table_row_spans(line):
        value = cell.strip(' \t')
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


def normalize_row(cells: list[CellSpan], size: int, end: int) -> list[CellSpan]:
    if len(cells) < size:
        return cells + [('', end, end)] * (size - len(cells))
    return cells[:size]


def split_table_row(line: str) -> list[str]:
    return [cell for cell, _, _ in split_table_row_spans(line)]


def split_table_row_spans(line: str) -> list[CellSpan]:
    original = line
    value = line.strip()
    value_start = len(original) - len(original.lstrip())
    value_end = value_start + len(value)
    if value_start < value_end and original[value_start] == '|':
        value_start += 1
    if value_start < value_end and original[value_end - 1] == '|' and not is_escaped(original, value_end - 1):
        value_end -= 1

    cells: list[CellSpan] = []
    start = value_start
    index = value_start
    code_marker = ''
    while index < value_end:
        char = original[index]
        if char == '\\':
            index += 2
            continue
        if char == '`':
            marker_end = index
            while marker_end < value_end and original[marker_end] == '`':
                marker_end += 1
            marker = original[index:marker_end]
            if code_marker == marker:
                code_marker = ''
            elif not code_marker:
                code_marker = marker
            index = marker_end
            continue
        if char == '|' and not code_marker:
            cells.append((original[start:index], start, index))
            start = index + 1
        index += 1

    cells.append((original[start:value_end], start, value_end))
    return cells


def has_unescaped_pipe(line: str) -> bool:
    return any(char == '|' and not is_escaped(line, index) for index, char in enumerate(line))


def unescape_table_pipes(value: str) -> str:
    parts: list[str] = []
    index = 0
    while index < len(value):
        if value[index] == '|' and is_escaped(value, index):
            parts.pop()
            parts.append('|')
        else:
            parts.append(value[index])
        index += 1
    return ''.join(parts)
