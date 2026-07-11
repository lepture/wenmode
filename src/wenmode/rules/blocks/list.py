from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, cast

from wenmode.nodes import List as ListNode
from wenmode.nodes import ListItem, Node, Paragraph, Position, Text
from wenmode.utils import count_indent, count_indent_from, expand_leading_tabs

from ..._parser.source import SourceCollector, SourceMap
from ..._parser.state import BlockState
from ..base import BlockRule, Rule

if TYPE_CHECKING:
    from wenmode.parser import Parser


MARKER_RE = re.compile(
    r'^(?P<indent>[ \t]{0,3})(?P<marker>(?P<bullet>[*+-])|(?P<ordered>\d{1,9})(?P<delimiter>[.)]))(?P<spaces>[ \t]+|$)(?P<rest>.*)$'
)
TASK_MARKER_RE = re.compile(r'^\[([ xX])][ \t]+')


@dataclass(frozen=True, slots=True)
class ListMarkerStyle:
    ordered: bool
    start: int | None
    delimiter: str | None
    bullet: str | None


class List(BlockRule):
    """Parse ordered and unordered lists.

    Markdown syntax:

    .. code-block:: markdown

       - item

    :param task: Parse GFM task list markers when ``True``.
    """

    name = 'list'
    pattern = r'[ \t]{0,3}(?:[*+-](?:[ \t]+|$)|\d{1,9}[.)](?:[ \t]+|$))'

    def __init__(self, task: bool = False) -> None:
        super().__init__()
        self.task = task

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> ListNode:
        first = cast(re.Match[str], MARKER_RE.match(state.line.rstrip('\r\n')))
        if state.depth >= parser.max_container_depth - 1:
            return parse_shallow_list(parser, state, first, task=self.task)

        style = list_marker_style(first)
        items: list[Node] = []
        spread = False

        thematic_break = parser.rules.get('thematic_break')
        first_nonblank_cache: dict[int, str | None] = {}

        while not state.done:
            item_start_index = state.index
            line = state.line.rstrip('\r\n')
            marker = parse_list_item_marker(line, style, bool(items), thematic_break)
            if marker is None:
                break
            item_text, source, item_spread = collect_list_item(parser, state, marker, first_nonblank_cache)
            spread = spread or item_spread
            item = ListItem(
                children=parser.parse_blocks(
                    item_text,
                    parent_state=state,
                    source=source,
                ),
                spread=item_spread,
            )
            item.position = state.source.position_between(item_start_index, state.index)
            if self.task:
                schedule_task_list_marker(state, item)
            items.append(item)

        return ListNode(children=items, ordered=style.ordered, start=style.start, spread=spread)


def parse_shallow_list(parser: Parser, state: BlockState, first: re.Match[str], task: bool = False) -> ListNode:
    style = list_marker_style(first)
    items: list[Node] = []

    while not state.done:
        item_start_index = state.index
        marker = current_list_marker(state)
        if marker is None or not marker_matches_style(marker, style):
            break

        text = collect_shallow_item_text(state, marker)
        item = shallow_list_item(parser, state, text)
        item.position = state.source.position_between(item_start_index, state.index)
        if task:
            schedule_task_list_marker(state, item)
        items.append(item)

    return ListNode(children=items, ordered=style.ordered, start=style.start)


def list_marker_style(marker: re.Match[str]) -> ListMarkerStyle:
    ordered = marker.group('ordered') is not None
    start = int(marker.group('ordered')) if ordered else None
    return ListMarkerStyle(
        ordered=ordered,
        start=start,
        delimiter=marker.group('delimiter'),
        bullet=marker.group('bullet'),
    )


def parse_list_item_marker(
    line: str,
    style: ListMarkerStyle,
    has_items: bool,
    thematic_break: Rule | None,
) -> re.Match[str] | None:
    marker = MARKER_RE.match(line)
    if marker is None:
        return None
    if has_items and isinstance(thematic_break, BlockRule) and re.match(thematic_break.pattern, line):
        return None
    if not marker_matches_style(marker, style):
        return None
    return marker


def marker_matches_style(marker: re.Match[str], style: ListMarkerStyle) -> bool:
    if style.ordered != (marker.group('ordered') is not None):
        return False
    if style.bullet is not None and marker.group('bullet') != style.bullet:
        return False
    if style.delimiter is not None and marker.group('delimiter') != style.delimiter:
        return False
    return True


def collect_list_item(
    parser: Parser,
    state: BlockState,
    marker: re.Match[str],
    first_nonblank_cache: dict[int, str | None],
) -> tuple[str, SourceMap | None, bool]:
    marker_indent, content_indent, first_line = first_list_item_line(marker)
    lines = [first_line]
    source = state.source.collect()
    source.add(state.index, marker.start('rest'), first_line)
    state.advance()
    item_spread = False
    item_has_nested_marker = line_has_list_marker(first_line)
    fence_char, fence_size = update_open_fence(first_line, '', 0)

    while not state.done:
        line = state.line
        next_marker = MARKER_RE.match(line.rstrip('\r\n'))
        if next_marker is not None and count_indent(next_marker.group('indent')) == marker_indent:
            break
        if line.strip() == '':
            item_spread, consumed = consume_blank_list_line(
                state,
                source,
                lines,
                content_indent,
                marker_indent,
                item_has_nested_marker,
                first_nonblank_cache,
                fence_char,
                item_spread,
            )
            if consumed:
                continue
            break
        if has_continuation_indent(line, content_indent):
            text = strip_continuation_indent(line, content_indent)
            source.add(state.index, continuation_source_offset(line, content_indent), text)
            lines.append(text)
            item_has_nested_marker = item_has_nested_marker or line_has_list_marker(text)
            fence_char, fence_size = update_open_fence(text, fence_char, fence_size)
            state.advance()
            continue
        if is_lazy_list_continuation(parser, state, lines):
            source.add(state.index, 0, line)
            lines.append(line)
            item_has_nested_marker = item_has_nested_marker or line_has_list_marker(line)
            fence_char, fence_size = update_open_fence(line, fence_char, fence_size)
            state.advance()
            continue
        break

    return ''.join(lines), source.map(), item_spread


def is_lazy_list_continuation(parser: Parser, state: BlockState, lines: list[str]) -> bool:
    return lines[-1].strip() != '' and not parser.is_paragraph_interrupt(state.line, state)


def consume_blank_list_line(
    state: BlockState,
    source: SourceCollector,
    lines: list[str],
    content_indent: int,
    marker_indent: int,
    item_has_nested_marker: bool,
    first_nonblank_cache: dict[int, str | None],
    fence_char: str,
    item_spread: bool,
) -> tuple[bool, bool]:
    blank_index = state.index
    state.advance()
    if current_list_marker(state) is not None:
        item_spread = True
    if not item_has_content(lines):
        return item_spread, False
    if not should_keep_blank_in_item(state, content_indent, marker_indent):
        return item_spread, False
    if not fence_char and blank_belongs_to_item(
        state,
        content_indent,
        marker_indent,
        item_has_nested_marker,
        first_nonblank_cache,
    ):
        item_spread = True
    lines.append('\n')
    source.add(blank_index, 0, '\n')
    return item_spread, True


def first_list_item_line(marker: re.Match[str]) -> tuple[int, int, str]:
    marker_indent = count_indent(marker.group('indent'))
    marker_width = len(marker.group('marker'))
    content_indent = marker_indent + marker_width + 1
    rest = marker.group('rest')
    if rest.strip() == '':
        return marker_indent, marker_indent + 2, rest + '\n'

    spaces = marker.group('spaces')
    if not spaces:
        return marker_indent, content_indent, rest + '\n'

    space_width = count_indent_from(spaces, marker_indent + marker_width) - (marker_indent + marker_width)
    if 1 <= space_width <= 4:
        return marker_indent, marker_indent + marker_width + space_width, rest + '\n'

    rest_column = marker_indent + marker_width + space_width
    rest = ' ' * (rest_column - content_indent) + rest
    return marker_indent, content_indent, rest + '\n'


def collect_shallow_item_text(state: BlockState, marker: re.Match[str]) -> str:
    text_lines = [marker.group('rest')]
    marker_indent = count_indent(marker.group('indent'))
    state.advance()
    while not state.done and not is_same_indent_list_marker(state.line, marker_indent):
        if state.line.strip():
            text_lines.append(state.line.strip())
        state.advance()
    return '\n'.join(part for part in text_lines if part).strip()


def shallow_list_item(parser: Parser, state: BlockState, text: str) -> ListItem:
    if text:
        children: list[Node] = [Paragraph(children=parser.parse_inlines(text, state))]
    else:
        children = []
    return ListItem(children=children)


def current_list_marker(state: BlockState) -> re.Match[str] | None:
    if state.done:
        return None
    return MARKER_RE.match(state.line.rstrip('\r\n'))


def is_same_indent_list_marker(line: str, marker_indent: int) -> bool:
    marker = MARKER_RE.match(line.rstrip('\r\n'))
    return marker is not None and count_indent(marker.group('indent')) == marker_indent


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


def blank_belongs_to_item(
    state: BlockState,
    content_indent: int,
    marker_indent: int,
    item_has_nested_marker: bool,
    first_nonblank_cache: dict[int, str | None],
) -> bool:
    if state.done:
        return True
    line = first_nonblank_from_current(state, first_nonblank_cache)
    if line is None:
        return True
    marker = MARKER_RE.match(line.rstrip('\r\n'))
    if marker is not None:
        return count_indent(marker.group('indent')) <= marker_indent
    return count_indent(line) <= content_indent or not item_has_nested_marker


def first_nonblank_from_current(state: BlockState, cache: dict[int, str | None]) -> str | None:
    if state.index in cache:
        return cache[state.index]

    offset = 0
    blank_indexes: list[int] = []
    while state.has(offset):
        index = state.index + offset
        if index in cache:
            line = cache[index]
            for blank_index in blank_indexes:
                cache[blank_index] = line
            return line
        line = state.peek(offset)
        if line.strip() != '':
            for blank_index in blank_indexes:
                cache[blank_index] = line
            cache[index] = line
            return line
        blank_indexes.append(index)
        offset += 1
    for blank_index in blank_indexes:
        cache[blank_index] = None
    return None


def line_has_list_marker(line: str) -> bool:
    return MARKER_RE.match(line.rstrip('\r\n')) is not None


def item_has_content(lines: list[str]) -> bool:
    return any(line.strip() for line in lines)


def update_open_fence(line: str, fence_char: str, fence_size: int) -> tuple[str, int]:
    if not fence_char:
        match = re.match(r'[ \t]{0,3}(`{3,}|~{3,})', line)
        if match is None:
            return '', 0
        return match.group(1)[0], len(match.group(1))
    if re.match(rf'[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*$', line.rstrip('\r\n')):
        return '', 0
    return fence_char, fence_size


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
