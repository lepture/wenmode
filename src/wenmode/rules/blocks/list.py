from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import List as ListNode
from wenmode.nodes import ListItem, Node, Paragraph, Position, Text
from wenmode.state import BlockState
from wenmode.utils import count_indent, count_indent_from, expand_leading_tabs

from ..base import BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


MARKER_RE = re.compile(
    r'^(?P<indent>[ \t]{0,3})(?P<marker>(?P<bullet>[*+-])|(?P<ordered>\d{1,9})(?P<delimiter>[.)]))(?P<spaces>[ \t]+|$)(?P<rest>.*)$'
)
TASK_MARKER_RE = re.compile(r'^\[([ xX])][ \t]+')


class List(BlockRule):
    """Parse ordered and unordered lists.

    Markdown syntax:

    .. code-block:: markdown

       - item

    :param task: Parse GFM task list markers when ``True``.
    """

    def __init__(self, task: bool = False) -> None:
        super().__init__('list', r'[ \t]{0,3}(?:[*+-](?:[ \t]+|$)|\d{1,9}[.)](?:[ \t]+|$))')
        self.task = task

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> ListNode:
        first = MARKER_RE.match(state.line.rstrip('\r\n'))
        if first is None:
            state.advance()
            return ListNode(children=[])
        if state.depth >= parser.max_container_depth - 1:
            return parse_shallow_list(parser, state, first, task=self.task)

        ordered = first.group('ordered') is not None
        if ordered:
            start = int(first.group('ordered'))
        else:
            start = None
        delimiter = first.group('delimiter')
        bullet = first.group('bullet')
        items: list[Node] = []
        spread = False

        thematic_break = parser.rules.get('thematic_break')

        while not state.done:
            item_start_index = state.index
            line = state.line.rstrip('\r\n')
            marker = MARKER_RE.match(line)
            if marker is None:
                break
            if items and isinstance(thematic_break, BlockRule) and re.match(thematic_break.pattern, line):
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
                elif space_width > 4:  # pragma: no branch
                    rest_column = marker_indent + marker_width + space_width
                    rest = ' ' * (rest_column - content_indent) + rest

            first_item_line = rest + '\n'
            item_lines = [first_item_line]
            source = state.source.collect()
            source.add(state.index, marker.start('rest'), first_item_line)
            state.advance()
            item_spread = False

            while not state.done:
                next_line = state.line
                next_marker = MARKER_RE.match(next_line.rstrip('\r\n'))
                if next_marker is not None and count_indent(next_marker.group('indent')) == marker_indent:
                    break
                if next_line.strip() == '':
                    blank_index = state.index
                    state.advance()
                    if state.done:
                        next_marker_after_blank = None
                    else:
                        next_marker_after_blank = MARKER_RE.match(state.line.rstrip('\r\n'))
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
                        source.add(blank_index, 0, '\n')
                        continue
                    break
                if has_continuation_indent(next_line, content_indent):
                    text = strip_continuation_indent(next_line, content_indent)
                    item_lines.append(text)
                    source.add(state.index, continuation_source_offset(next_line, content_indent), text)
                    state.advance()
                    continue
                if item_lines and item_lines[-1].strip() != '' and not parser.is_paragraph_interrupt(next_line, state):
                    item_lines.append(next_line)
                    source.add(state.index, 0, next_line)
                    state.advance()
                    continue
                break

            item_text = ''.join(item_lines)
            item = ListItem(
                children=parser.parse_blocks(
                    item_text,
                    parent_state=state,
                    source=source.map(),
                ),
                spread=item_spread,
            )
            item.position = state.source.position_between(item_start_index, state.index)
            if self.task:
                schedule_task_list_marker(state, item)
            items.append(item)

            if item_spread:
                while not state.done and state.line.strip() == '':
                    state.advance()  # pragma: no cover

        return ListNode(children=items, ordered=ordered, start=start, spread=spread)


def parse_shallow_list(parser: Parser, state: BlockState, first: re.Match[str], task: bool = False) -> ListNode:
    ordered = first.group('ordered') is not None
    if ordered:
        start = int(first.group('ordered'))
    else:
        start = None
    delimiter = first.group('delimiter')
    bullet = first.group('bullet')
    items: list[Node] = []

    while not state.done:
        item_start_index = state.index
        marker = MARKER_RE.match(state.line.rstrip('\r\n'))
        if marker is None:
            break
        if ordered != (marker.group('ordered') is not None):
            break
        if bullet is not None and marker.group('bullet') != bullet:
            break
        if delimiter is not None and marker.group('delimiter') != delimiter:
            break

        text_lines = [marker.group('rest')]
        state.advance()
        while not state.done:
            line = state.line
            next_marker = MARKER_RE.match(line.rstrip('\r\n'))
            marker_indent = marker.group('indent')
            if next_marker is not None and count_indent(next_marker.group('indent')) == count_indent(marker_indent):
                break
            if line.strip():
                text_lines.append(line.strip())
            state.advance()

        text = '\n'.join(part for part in text_lines if part).strip()
        if text:
            children: list[Node] = [Paragraph(children=parser.parse_inlines(text, state))]
        else:
            children = []
        item = ListItem(children=children)
        item.position = state.source.position_between(item_start_index, state.index)
        if task:
            schedule_task_list_marker(state, item)
        items.append(item)

    return ListNode(children=items, ordered=ordered, start=start)


def schedule_task_list_marker(state: BlockState, item: ListItem) -> None:
    if state.defer_inlines:
        state.pending_inline_callbacks.append(lambda: apply_task_list_marker(item))
    else:
        apply_task_list_marker(item)


def apply_task_list_marker(item: ListItem) -> None:
    if not item.children or not isinstance(item.children[0], Paragraph):
        return

    paragraph = item.children[0]
    if not paragraph.children or not isinstance(paragraph.children[0], Text):
        return

    text = paragraph.children[0]
    match = TASK_MARKER_RE.match(text.value)
    if match is None:
        return

    item.checked = match.group(1).lower() == 'x'
    if text.position is not None:
        text.position = Position(start=text.position.start + match.end(), end=text.position.start + len(text.value))
    text.value = text.value[match.end() :]
    if text.value == '':
        paragraph.children.pop(0)


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


def blank_belongs_to_item(item_lines: list[str], state: BlockState, content_indent: int, marker_indent: int) -> bool:
    if state.done:
        return True
    line = state.first_nonblank_from_current()
    if line is None:
        return True
    marker = MARKER_RE.match(line.rstrip('\r\n'))
    if marker is not None:
        return count_indent(marker.group('indent')) <= marker_indent
    return count_indent(line) <= content_indent or not has_nested_list(item_lines)


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
    if len(expanded) >= columns:
        return expanded[columns:]
    return ''


def continuation_source_offset(line: str, columns: int) -> int:
    index = 0
    width = 0
    while index < len(line) and width < columns:
        char = line[index]
        if char == '\t':
            width += 4 - width % 4
        else:
            width += 1
        index += 1
    return index
