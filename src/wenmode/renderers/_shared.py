from __future__ import annotations

import re

from wenmode.nodes import Table, TableCell, TableRow

from .base import BaseRenderer, RenderContext

_FOOTNOTE_LABEL_RE = re.compile(r'[^A-Za-z0-9_.:-]+')


def table_rows(node: Table) -> list[list[TableCell]]:
    return [
        [cell for cell in row.children if isinstance(cell, TableCell)]
        for row in node.children
        if isinstance(row, TableRow)
    ]


def render_table_cell_content(renderer: BaseRenderer, cell: TableCell, context: RenderContext) -> str:
    return renderer.render_children(cell.children, context).replace('\n', ' ').strip()


def footnote_label(value: str) -> str:
    label = _FOOTNOTE_LABEL_RE.sub('-', value).strip('-')
    return label or 'footnote'
