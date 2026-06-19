from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Emphasis as EmphasisNode
from wenmode.nodes import Node, Position
from wenmode.nodes import Strong as StrongNode
from wenmode.nodes import Text as TextNode
from wenmode.state import BlockState

from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


class Emphasis(InlineRule):
    """Parse emphasis and strong emphasis delimiters.

    Markdown syntax:

    .. code-block:: markdown

       *emphasis* and **strong**
    """

    def __init__(self) -> None:
        super().__init__('emphasis', r'(?:\*+|_+)')

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        return None, match.start()


@dataclass
class Delimiter:
    index: int
    marker: str
    length: int
    can_open: bool
    can_close: bool


def parse_emphasis_sequence(nodes: list[Node]) -> list[Node]:
    parts: list[Node] = []
    delimiters: list[Delimiter] = []
    source = source_text(nodes)

    source_pos = 0
    for node in nodes:
        if isinstance(node, TextNode) and node._parse_emphasis:
            split_text_node(node, source, source_pos, parts, delimiters)
            source_pos += len(node.value)
        else:
            parts.append(node)
            source_pos += source_length(node)

    process_delimiters(parts, delimiters)
    return [part for part in parts if not (isinstance(part, TextNode) and part.value == '')]


def source_text(nodes: list[Node]) -> str:
    values = []
    for node in nodes:
        if isinstance(node, TextNode):
            values.append(node.value)
        else:
            values.append(placeholder_text(node))
    return ''.join(values)


def source_length(node: Node) -> int:
    if isinstance(node, TextNode):
        return len(node.value)
    return len(placeholder_text(node))


def placeholder_text(node: Node) -> str:
    return '\ufffc'


def split_text_node(
    node: TextNode,
    source: str,
    source_start: int,
    parts: list[Node],
    delimiters: list[Delimiter],
) -> None:
    text = node.value
    pos = 0
    while pos < len(text):
        if text[pos] not in '*_':
            next_pos = next_delimiter_run(text, pos)
            if node.position is None:
                position = None
            else:
                position = Position(start=node.position.start + pos, end=node.position.start + next_pos)
            parts.append(TextNode(value=text[pos:next_pos], position=position))
            pos = next_pos
            continue

        marker = text[pos]
        end = pos
        while end < len(text) and text[end] == marker:
            end += 1
        run_length = end - pos
        delimiter_length = run_length
        absolute = source_start + pos
        opener = can_open(source, absolute, run_length, marker)
        closer = can_close(source, absolute, run_length, marker)
        part_index = len(parts)
        if node.position is None:
            position = None
        else:
            position = Position(start=node.position.start + pos, end=node.position.start + end)
        parts.append(TextNode(value=text[pos:end], position=position))
        if opener or closer:
            delimiters.append(Delimiter(part_index, marker, delimiter_length, opener, closer))
        pos = end


def next_delimiter_run(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index] not in '*_':
        index += 1
    return index


def process_delimiters(parts: list[Node], delimiters: list[Delimiter]) -> None:
    closer_pos = 0
    openers_bottom: dict[tuple[str, int, bool], int] = {}
    while closer_pos < len(delimiters):
        closer = delimiters[closer_pos]
        if not closer.can_close or closer.length == 0:
            closer_pos += 1
            continue

        opener_key = (closer.marker, closer.length % 3, closer.can_open)
        opener_pos = closer_pos - 1
        opener_bottom = openers_bottom.get(opener_key, 0)
        opener: Delimiter | None = None
        while opener_pos >= opener_bottom:
            candidate = delimiters[opener_pos]
            if (
                candidate.marker == closer.marker
                and candidate.can_open
                and candidate.length > 0
                and can_match_delimiters(candidate, closer)
            ):
                opener = candidate
                break
            opener_pos -= 1

        if opener is None:
            openers_bottom[opener_key] = closer_pos
            closer_pos += 1
            continue

        if opener.length >= 2 and closer.length >= 2:
            use_length = 2
        else:
            use_length = 1
        if use_length == 2 and not has_strong_enabled(parts, opener, closer):
            use_length = 1
        if use_length == 1 and not has_emphasis_enabled(parts, opener, closer):
            closer_pos += 1
            continue
        if not has_content(parts, opener.index + 1, closer.index):
            closer_pos += 1
            continue

        opener_text = parts[opener.index]
        closer_text = parts[closer.index]
        if not isinstance(opener_text, TextNode) or not isinstance(closer_text, TextNode):
            closer_pos += 1
            continue

        node_position = emphasis_position(opener_text, closer_text, use_length)
        if opener_text.position is None:
            remaining_opener_position = None
        else:
            remaining_opener_position = Position(
                start=opener_text.position.start,
                end=opener_text.position.start + len(opener_text.value) - use_length,
            )
        if closer_text.position is None:
            remaining_closer_position = None
        else:
            remaining_closer_position = Position(
                start=closer_text.position.start + use_length,
                end=closer_text.position.start + len(closer_text.value),
            )
        opener_text.value = opener_text.value[:-use_length]
        closer_text.value = closer_text.value[use_length:]
        opener_text.position = remaining_opener_position
        closer_text.position = remaining_closer_position
        children = parts[opener.index + 1 : closer.index]
        if use_length == 2:
            node: Node = StrongNode(children=children)
        else:
            node = EmphasisNode(children=children)
        node.position = node_position
        old_closer_index = closer.index
        parts[opener.index + 1 : old_closer_index] = [node]

        removed = old_closer_index - opener.index - 2
        closer.index = opener.index + 2
        if removed:
            for delimiter in delimiters:
                if opener.index < delimiter.index < old_closer_index:
                    delimiter.length = 0
                elif delimiter.index >= old_closer_index:
                    delimiter.index -= removed

        opener.length -= use_length
        closer.length -= use_length
        if opener.length == 0:
            opener.can_open = False
        if closer.length == 0:
            closer.can_close = False

        if opener.can_open or closer.can_close:
            closer_pos = max(opener_pos, openers_bottom.get(opener_key, 0))
        else:
            closer_pos += 1


def has_strong_enabled(parts: list[Node], opener: Delimiter, closer: Delimiter) -> bool:
    return len(text_value(parts[opener.index])) >= 2 and len(text_value(parts[closer.index])) >= 2


def has_emphasis_enabled(parts: list[Node], opener: Delimiter, closer: Delimiter) -> bool:
    return bool(text_value(parts[opener.index]) and text_value(parts[closer.index]))


def text_value(node: Node) -> str:
    if isinstance(node, TextNode):
        return node.value
    return ''


def has_content(parts: list[Node], start: int, end: int) -> bool:
    return any(not isinstance(part, TextNode) or part.value != '' for part in parts[start:end])


def emphasis_position(opener: TextNode, closer: TextNode, size: int) -> Position | None:
    if opener.position is None or closer.position is None:
        return None
    return Position(start=opener.position.end - size, end=closer.position.start + size)


def can_match_delimiters(opener: Delimiter, closer: Delimiter) -> bool:
    if opener.can_close or closer.can_open:
        return (opener.length + closer.length) % 3 != 0 or opener.length % 3 == 0 and closer.length % 3 == 0
    return True


def can_open(text: str, start: int, size: int, marker: str) -> bool:
    if start > 0:
        previous = text[start - 1]
    else:
        previous = '\n'
    if start + size < len(text):
        next_char = text[start + size]
    else:
        next_char = '\n'
    if marker == '_' and previous.isalnum() and next_char.isalnum():
        return False
    if next_char.isspace():
        return False
    if is_punctuation(next_char) and not previous.isspace() and not is_punctuation(previous):
        return False
    return True


def can_close(text: str, start: int, size: int, marker: str) -> bool:
    if start > 0:
        previous = text[start - 1]
    else:
        previous = '\n'
    if start + size < len(text):
        next_char = text[start + size]
    else:
        next_char = '\n'
    if marker == '_' and previous.isalnum() and next_char.isalnum():
        return False
    if previous.isspace():
        return False
    if is_punctuation(previous) and not next_char.isspace() and not is_punctuation(next_char):
        return False
    return True


def is_punctuation(char: str) -> bool:
    return not char.isspace() and not char.isalnum()
