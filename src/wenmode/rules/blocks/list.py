from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import List as ListNode
from wenmode.nodes import ListItem, Node
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


MARKER_RE = re.compile(
    r'^(?P<indent>[ \t]{0,3})(?P<marker>(?P<bullet>[*+-])|(?P<ordered>\d{1,9})(?P<delimiter>[.)]))(?P<spaces>[ \t]+|$)(?P<rest>.*)$'
)


class List(BlockRule):
    def __init__(self) -> None:
        super().__init__('list', r'[ \t]{0,3}(?:[*+-](?:[ \t]+|$)|\d{1,9}[.)](?:[ \t]+|$))')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> ListNode:
        first = MARKER_RE.match(state.line.rstrip('\r\n'))
        if first is None:
            state.advance()
            return ListNode(children=[])

        ordered = first.group('ordered') is not None
        start = int(first.group('ordered')) if ordered else None
        delimiter = first.group('delimiter')
        bullet = first.group('bullet')
        items: list[Node] = []
        spread = False

        while not state.done:
            line = state.line.rstrip('\r\n')
            marker = MARKER_RE.match(line)
            if marker is None:
                break
            if items and is_thematic_break(line):
                break
            if ordered != (marker.group('ordered') is not None):
                break
            if bullet is not None and marker.group('bullet') != bullet:
                break
            if delimiter is not None and marker.group('delimiter') != delimiter:
                break

            marker_indent = count_indent(marker.group('indent'))
            marker_width = len(marker.group('marker'))
            spaces = marker.group('spaces')
            rest = marker.group('rest')
            content_indent = marker_indent + marker_width + 1
            if rest.strip() == '':
                content_indent = marker_indent + 2
            if spaces:
                space_width = count_indent_from(spaces, marker_indent + marker_width) - (marker_indent + marker_width)
                if rest.strip() == '':
                    content_indent = marker_indent + 2
                elif 1 <= space_width <= 4:
                    content_indent = marker_indent + marker_width + space_width
                elif space_width > 4:
                    rest_column = marker_indent + marker_width + space_width
                    rest = ' ' * (rest_column - content_indent) + rest

            item_lines = [rest + '\n']
            state.advance()
            item_spread = False

            while not state.done:
                next_line = state.line
                next_marker = MARKER_RE.match(next_line.rstrip('\r\n'))
                if next_marker is not None and count_indent(next_marker.group('indent')) == marker_indent:
                    break
                if next_line.strip() == '':
                    state.advance()
                    next_marker_after_blank = MARKER_RE.match(state.line.rstrip('\r\n')) if not state.done else None
                    if next_marker_after_blank is not None:
                        item_spread = True
                        spread = True
                    if item_has_content(item_lines) and should_keep_blank_in_item(state, content_indent, marker_indent):
                        if not has_open_fence(item_lines) and blank_belongs_to_item(
                            item_lines, state, content_indent, marker_indent
                        ):
                            item_spread = True
                            spread = True
                        item_lines.append('\n')
                        continue
                    break
                    continue
                if has_continuation_indent(next_line, content_indent):
                    item_lines.append(strip_continuation_indent(next_line, content_indent))
                    state.advance()
                    continue
                if item_lines and item_lines[-1].strip() != '' and not parser.is_paragraph_interrupt(next_line):
                    item_lines.append(next_line)
                    state.advance()
                    continue
                break

            items.append(ListItem(children=parser.parse_blocks(''.join(item_lines)), spread=item_spread))

            if item_spread:
                while not state.done and state.line.strip() == '':
                    state.advance()

        return ListNode(children=items, ordered=ordered, start=start, spread=spread)


def should_keep_blank_in_item(state: BlockState, content_indent: int, marker_indent: int) -> bool:
    if state.done:
        return False
    if state.line.strip() == '':
        return True
    marker = MARKER_RE.match(state.line.rstrip('\r\n'))
    if marker is not None and count_indent(marker.group('indent')) == marker_indent:
        return True
    if marker is not None and count_indent(marker.group('indent')) < content_indent:
        return False
    return has_continuation_indent(state.line, content_indent)


def blank_belongs_to_item(
    item_lines: list[str], state: BlockState, content_indent: int, marker_indent: int
) -> bool:
    if state.done:
        return True
    line = first_nonblank_line(state)
    if line is None:
        return True
    marker = MARKER_RE.match(line.rstrip('\r\n'))
    if marker is not None:
        return count_indent(marker.group('indent')) <= marker_indent
    return count_indent(line) <= content_indent or not has_nested_list(item_lines)


def first_nonblank_line(state: BlockState) -> str | None:
    index = state.index
    while index < len(state.lines):
        line = state.lines[index]
        if line.strip() != '':
            return line
        index += 1
    return None


def has_nested_list(lines: list[str]) -> bool:
    for line in lines:
        if MARKER_RE.match(line.rstrip('\r\n')) is not None:
            return True
    return False


def item_has_content(lines: list[str]) -> bool:
    return any(line.strip() for line in lines)


def has_open_fence(lines: list[str]) -> bool:
    fence_char = ''
    fence_size = 0
    for line in lines:
        if not fence_char:
            match = re.match(r'[ \t]{0,3}(`{3,}|~{3,})', line)
            if match is not None:
                fence_char = match.group(1)[0]
                fence_size = len(match.group(1))
            continue
        if re.match(rf'[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*$', line.rstrip('\r\n')):
            fence_char = ''
            fence_size = 0
    return bool(fence_char)


def has_continuation_indent(line: str, columns: int) -> bool:
    return count_indent(line) >= columns


def strip_continuation_indent(line: str, columns: int) -> str:
    expanded = expand_leading_tabs(line)
    return expanded[columns:] if len(expanded) >= columns else ''


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
    column = 0
    column += start_column
    for char in text:
        if char == ' ':
            column += 1
        elif char == '\t':
            column += 4 - column % 4
        else:
            break
    return column


def is_thematic_break(line: str) -> bool:
    return bool(
        re.match(r'[ \t]{0,3}(?:\*[ \t]*){3,}$', line)
        or re.match(r'[ \t]{0,3}(?:-[ \t]*){3,}$', line)
        or re.match(r'[ \t]{0,3}(?:_[ \t]*){3,}$', line)
    )
