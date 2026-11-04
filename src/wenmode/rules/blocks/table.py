from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node, TableCell, TableRow
from wenmode.nodes import Table as TableNode
from wenmode.utils import count_indent_from, is_escaped

from ..._parser.rule_base import BlockCandidate, BlockRule
from ..._parser.source import SourceMap
from ..._parser.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


DELIMITER_CELL_RE = re.compile(r'^:?-+:?$')
DELIMITER_ROW_CHARS_RE = re.compile(r'[ \t|:-]+')
DELIMITER_ROW_START_RE = re.compile(r'\s*[|:-]')
SETEXT_DASHES_RE = re.compile(r' {0,3}-+[ \t]*$')
CellSpan = tuple[str, int, int]


class Table(BlockRule):
    """Parse GFM pipe tables.

    Markdown syntax:

    .. code-block:: markdown

       | A | B |
       | --- | --- |
       | x | y |
    """

    name = 'table'
    pattern = r' {0,3}[^|\r\n]*\|'

    def __init__(self, require_body_pipe: bool = True) -> None:
        super().__init__()
        self.require_body_pipe = require_body_pipe

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> TableNode | None:
        if not state.has(1):
            return None

        header_line = state.line.rstrip('\r\n')
        parsed_header = parse_table_header(header_line, state.peek(1).rstrip('\r\n'))
        if parsed_header is None:
            return None
        header_cells, align = parsed_header

        header = TableRow(children=parse_cells(parser, header_cells, state, state.index))
        header.position = state.source.position_between(state.index, state.index + 1)
        rows: list[Node] = [header]
        state.advance(2)

        while not state.done:
            line = state.line.rstrip('\r\n')
            if (
                line.strip() == ''
                or count_indent_from(line) >= 4
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

    def interrupts_paragraph(self, parser: Parser, state: BlockState) -> bool:
        """Return whether a paragraph line and the delimiter row below it start a table.

        Only paragraph parsing asks this: a lazy continuation line or a table body
        row never starts a table.
        """
        if '|' not in state.line or not state.has(1):
            return False
        delimiter_line = state.peek(1)
        if DELIMITER_ROW_START_RE.match(delimiter_line) is None or not starts_table(state):
            return False
        # A setext underline takes precedence over a delimiter row without pipes.
        return 'setext_heading' not in parser.rules or SETEXT_DASHES_RE.match(delimiter_line.rstrip('\r\n')) is None

    def is_delimiter_attempt(self, line: str) -> bool:
        """Return whether a paragraph line is a delimiter row tried against the line above as a table header."""
        if '-' not in line or DELIMITER_ROW_START_RE.match(line) is None:
            return False
        return count_indent_from(line) < 4 and is_delimiter_row(line)


def starts_table(state: BlockState) -> bool:
    """Return whether the current line is a header row followed by a matching delimiter row."""
    if not state.has(1) or '|' not in state.line:
        return False
    return parse_table_header(state.line.rstrip('\r\n'), state.peek(1).rstrip('\r\n')) is not None


def parse_table_header(header_line: str, delimiter_line: str) -> tuple[list[CellSpan], list[str | None]] | None:
    align = parse_delimiter_row(delimiter_line)
    if (
        align is None
        or count_indent_from(header_line) >= 4
        or count_indent_from(delimiter_line) >= 4
        or not has_unescaped_pipe(header_line)
    ):
        return None
    header_cells = split_table_row_spans(header_line)
    if len(header_cells) != len(align):
        return None
    return header_cells, align


def parse_cells(parser: Parser, cells: list[CellSpan], state: BlockState, line_index: int) -> list[Node]:
    parsed: list[Node] = []
    with state.nested_content():
        for raw, start, end in cells:
            stripped = raw.strip()
            leading = len(raw) - len(raw.lstrip())
            source = state.source.line_text(line_index, start + leading, stripped)
            text, source = unescape_table_pipes(stripped, source)
            cell = TableCell(children=parser.parse_inlines(text, state, source=source))
            cell.position = state.source.line_position(line_index, start, end)
            parsed.append(cell)
    return parsed


def has_table_rule(parser: Parser) -> bool:
    return isinstance(parser.rules.get('table'), Table)


def is_delimiter_row(line: str) -> bool:
    return parse_delimiter_row(line.rstrip('\r\n')) is not None


def completes_table_header(lines: list[str], line: str) -> bool:
    """Return whether ``line`` is a delimiter row matching the last of ``lines`` as a header row."""
    if not lines or '-' not in line or DELIMITER_ROW_START_RE.match(line) is None:
        return False
    return parse_table_header(lines[-1].rstrip('\r\n'), line.rstrip('\r\n')) is not None


def table_open_after(parser: Parser, table_open: bool, lines: list[str], line: str) -> bool:
    """Return whether container content has an open table once ``line`` follows ``lines``."""
    return completes_table_header(lines, line) or (table_open and continues_table_body(parser, line))


def continues_table_body(parser: Parser, line: str) -> bool:
    """Return whether ``line`` continues an open table, as :meth:`Table.parse` decides."""
    text = line.rstrip('\r\n')
    if text.strip() == '' or count_indent_from(text) >= 4 or parser.is_paragraph_interrupt(text):
        return False
    table = parser.rules.get('table')
    return not (isinstance(table, Table) and table.require_body_pipe) or has_unescaped_pipe(text)


def parse_delimiter_row(line: str) -> list[str | None] | None:
    # Reject most lines before splitting: a delimiter row holds only these characters.
    if DELIMITER_ROW_CHARS_RE.fullmatch(line.strip()) is None:
        return None
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
    while index < value_end:
        char = original[index]
        if char == '\\':
            index += 2
            continue
        if char == '|':
            cells.append((original[start:index], start, index))
            start = index + 1
        index += 1

    cells.append((original[start:value_end], start, value_end))
    return cells


def has_unescaped_pipe(line: str) -> bool:
    return any(char == '|' and not is_escaped(line, index) for index, char in enumerate(line))


def unescape_table_pipes(value: str, source: SourceMap | None) -> tuple[str, SourceMap | None]:
    text_parts: list[str] = []
    source_parts: list[tuple[str, int]] = []
    segment_start = 0
    for index, char in enumerate(value):
        if char != '|' or not is_escaped(value, index):
            continue

        backslash = index - 1
        segment = value[segment_start:backslash]
        text_parts.append(segment)
        if source is not None:
            if segment:
                source_parts.append((segment, source.source_offset(segment_start)))
            # Keep the deleted backslash as a zero-width source segment so
            # node ranges spanning the pipe still include the escape.
            source_parts.append(('', source.source_offset(backslash)))
        segment_start = index

    if segment_start == 0:
        return value, source

    segment = value[segment_start:]
    text_parts.append(segment)
    if source is not None and segment:
        source_parts.append((segment, source.source_offset(segment_start)))
    text = ''.join(text_parts)
    return text, SourceMap.from_parts(source_parts) if source is not None else None
