from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Emphasis as EmphasisNode
from wenmode.nodes import Node, Parent, Position
from wenmode.nodes import Strong as StrongNode
from wenmode.nodes import Text as TextNode
from wenmode.utils.cjk import (
    is_cjk_character,
    is_ideographic_variation_selector,
    is_non_cjk_punctuation,
    is_punctuation,
)

from ..._parser.state import BlockState
from ..base import InlineCandidate, InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser

_PLACEHOLDER_TEXT = '\ufffc'


class Emphasis(InlineRule):
    """Parse emphasis and strong emphasis delimiters.

    Markdown syntax:

    .. code-block:: markdown

       *emphasis* and **strong**
    """

    name = 'emphasis'
    pattern = r'(?:\*+|_+)'

    def __init__(self, cjk_friendly: bool = False) -> None:
        super().__init__()
        self.cjk_friendly = cjk_friendly

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        return None, candidate.start

    def parse_emphasis_sequence(self, nodes: list[Node], max_depth: int = 20) -> list[Node]:
        return parse_emphasis_sequence(nodes, cjk_friendly=self.cjk_friendly, max_depth=max_depth)


@dataclass(slots=True)
class Delimiter:
    index: int
    marker: str
    length: int
    can_open: bool
    can_close: bool
    orig_length: int


def parse_emphasis_sequence(nodes: list[Node], cjk_friendly: bool = False, max_depth: int = 20) -> list[Node]:
    parts: list[Node] = []
    delimiters: list[Delimiter] = []
    source = source_text(nodes)

    source_pos = 0
    for node in nodes:
        if isinstance(node, TextNode) and node._parse_emphasis:
            split_text_node(node, source, source_pos, parts, delimiters, cjk_friendly=cjk_friendly)
            source_pos += len(node.value)
        else:
            parts.append(node)
            source_pos += source_length(node)

    if process_flat_non_nested_delimiters(parts, delimiters, max_depth=max_depth):
        return [part for part in parts if not (isinstance(part, TextNode) and part.value == '')]
    process_delimiters(parts, delimiters, max_depth=max_depth)
    return [part for part in parts if not (isinstance(part, TextNode) and part.value == '')]


def source_text(nodes: list[Node]) -> str:
    values = []
    for node in nodes:
        if isinstance(node, TextNode):
            values.append(node.value)
        else:
            values.append(_PLACEHOLDER_TEXT)
    return ''.join(values)


def source_length(node: Node) -> int:
    if isinstance(node, TextNode):
        return len(node.value)
    return len(_PLACEHOLDER_TEXT)


def split_text_node(
    node: TextNode,
    source: str,
    source_start: int,
    parts: list[Node],
    delimiters: list[Delimiter],
    cjk_friendly: bool = False,
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
        opener = can_open(source, absolute, run_length, marker, cjk_friendly=cjk_friendly)
        closer = can_close(source, absolute, run_length, marker, cjk_friendly=cjk_friendly)
        part_index = len(parts)
        if node.position is None:
            position = None
        else:
            position = Position(start=node.position.start + pos, end=node.position.start + end)
        parts.append(TextNode(value=text[pos:end], position=position))
        if opener or closer:
            delimiters.append(Delimiter(part_index, marker, delimiter_length, opener, closer, delimiter_length))
        pos = end


def next_delimiter_run(text: str, start: int) -> int:
    index = start
    while index < len(text) and text[index] not in '*_':
        index += 1
    return index


def process_flat_non_nested_delimiters(
    parts: list[Node], delimiters: list[Delimiter], max_depth: int = 20
) -> bool:
    if max_depth <= 0 or len(delimiters) < 2:
        return False
    for delimiter in delimiters:
        if delimiter.length != 1:
            return False
        part = parts[delimiter.index]
        if not isinstance(part, TextNode) or len(part.value) != 1:
            return False

    matches: list[tuple[int, int, EmphasisNode]] = []
    opener_stacks: dict[str, list[int]] = {'*': [], '_': []}
    for closer_pos, closer in enumerate(delimiters):
        matched = False
        if closer.can_close:
            stack = opener_stacks[closer.marker]
            while stack:
                opener_pos = stack.pop()
                opener = delimiters[opener_pos]
                if not is_matching_opener(opener, closer):
                    continue
                if closer_pos - opener_pos > 2:
                    return False
                node = flat_emphasis_node(parts, opener, closer, max_depth)
                if node is None:
                    return False
                matches.append((opener.index, closer.index, node))
                matched = True
                break
        if not matched and closer.can_open:
            opener_stacks[closer.marker].append(closer_pos)

    if not matches:
        return False

    result: list[Node] = []
    index = 0
    for opener_index, closer_index, node in matches:
        if opener_index < index:
            return False
        result.extend(parts[index:opener_index])
        result.append(node)
        index = closer_index + 1
    result.extend(parts[index:])
    parts[:] = result
    return True


def flat_emphasis_node(
    parts: list[Node], opener: Delimiter, closer: Delimiter, max_depth: int
) -> EmphasisNode | None:
    use_length, opener_text, closer_text = prepare_delimiter_match(parts, opener, closer, max_depth)
    if use_length != 1 or opener_text is None or closer_text is None:
        return None
    node = EmphasisNode(children=parts[opener.index + 1 : closer.index])
    node.position = emphasis_position(opener_text, closer_text, 1)
    return node


def process_delimiters(parts: list[Node], delimiters: list[Delimiter], max_depth: int = 20) -> None:
    closer_pos = 0
    openers_bottom: dict[tuple[str, int, bool], int] = {}
    while closer_pos < len(delimiters):
        closer = delimiters[closer_pos]
        if not closer.can_close or closer.length == 0:
            closer_pos += 1
            continue

        opener_key = (closer.marker, closer.length % 3, closer.can_open)
        opener_bottom = openers_bottom.get(opener_key, 0)
        opener_pos, opener = find_matching_opener(delimiters, closer, closer_pos, opener_bottom)
        if opener is None:
            openers_bottom[opener_key] = closer_pos
            closer_pos += 1
            continue

        use_length, opener_text, closer_text = prepare_delimiter_match(parts, opener, closer, max_depth)
        if use_length == 0 or opener_text is None or closer_text is None:
            closer_pos += 1
            continue

        apply_delimiter_match(parts, delimiters, opener, closer, use_length, opener_text, closer_text)
        if opener.can_open or closer.can_close:
            closer_pos = max(opener_pos, openers_bottom.get(opener_key, 0))
        else:
            closer_pos += 1


def find_matching_opener(
    delimiters: list[Delimiter], closer: Delimiter, closer_pos: int, opener_bottom: int
) -> tuple[int, Delimiter | None]:
    opener_pos = closer_pos - 1
    while opener_pos >= opener_bottom:
        candidate = delimiters[opener_pos]
        if is_matching_opener(candidate, closer):
            return opener_pos, candidate
        opener_pos -= 1
    return opener_pos, None


def is_matching_opener(candidate: Delimiter, closer: Delimiter) -> bool:
    return (
        candidate.marker == closer.marker
        and candidate.can_open
        and candidate.length > 0
        and can_match_delimiters(candidate, closer)
    )


def prepare_delimiter_match(
    parts: list[Node], opener: Delimiter, closer: Delimiter, max_depth: int = 20
) -> tuple[int, TextNode | None, TextNode | None]:
    if opener.length >= 2 and closer.length >= 2:
        length = 2
    else:
        length = 1
    if length == 2 and not has_strong_enabled(parts, opener, closer):
        length = 1
    if length == 1 and not has_emphasis_enabled(parts, opener, closer):
        return 0, None, None
    if not has_content(parts, opener.index + 1, closer.index):
        return 0, None, None
    if emphasis_depth(parts[opener.index + 1 : closer.index]) >= max_depth:
        return 0, None, None

    opener_text = parts[opener.index]
    closer_text = parts[closer.index]
    if not isinstance(opener_text, TextNode) or not isinstance(closer_text, TextNode):
        return 0, None, None
    return length, opener_text, closer_text


def apply_delimiter_match(
    parts: list[Node],
    delimiters: list[Delimiter],
    opener: Delimiter,
    closer: Delimiter,
    use_length: int,
    opener_text: TextNode,
    closer_text: TextNode,
) -> None:
    old_closer_index = closer.index
    node_position = emphasis_position(opener_text, closer_text, use_length)
    if opener_text.position is None:
        remaining_opener_position = None
    else:
        remaining_opener_position = Position(
            start=opener_text.position.start, end=opener_text.position.start + len(opener_text.value) - use_length
        )
    if closer_text.position is None:
        remaining_closer_position = None
    else:
        remaining_closer_position = Position(
            start=closer_text.position.start + use_length, end=closer_text.position.start + len(closer_text.value)
        )
    opener_text.value = opener_text.value[: len(opener_text.value) - use_length]
    closer_text.value = closer_text.value[use_length:]
    opener_text.position = remaining_opener_position
    closer_text.position = remaining_closer_position

    children = parts[opener.index + 1 : closer.index]
    if use_length == 2:
        node: Node = StrongNode(children=children)
    else:
        node = EmphasisNode(children=children)
    node.position = node_position
    parts[opener.index + 1 : old_closer_index] = [node]
    update_delimiter_indices(delimiters, opener, closer, old_closer_index)
    update_delimiter_lengths(opener, closer, use_length)


def update_delimiter_indices(
    delimiters: list[Delimiter], opener: Delimiter, closer: Delimiter, old_closer_index: int
) -> None:
    removed = old_closer_index - opener.index - 2
    closer.index = opener.index + 2
    if not removed:
        return
    for delimiter in delimiters:
        if opener.index < delimiter.index < old_closer_index:
            delimiter.length = 0
        elif delimiter.index >= old_closer_index:
            delimiter.index -= removed


def update_delimiter_lengths(opener: Delimiter, closer: Delimiter, use_length: int) -> None:
    opener.length -= use_length
    closer.length -= use_length
    if opener.length == 0:
        opener.can_open = False
    if closer.length == 0:
        closer.can_close = False


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


def emphasis_depth(nodes: list[Node]) -> int:
    max_depth = 0
    stack: list[tuple[Node, int]] = [(node, 0) for node in nodes]
    while stack:
        node, parent_depth = stack.pop()
        if isinstance(node, (EmphasisNode, StrongNode)):
            depth = parent_depth + 1
            if depth > max_depth:
                max_depth = depth
        else:
            depth = parent_depth
        if isinstance(node, Parent):
            stack.extend((child, depth) for child in node.children)
    return max_depth


def emphasis_position(opener: TextNode, closer: TextNode, size: int) -> Position | None:
    if opener.position is None or closer.position is None:
        return None
    return Position(start=opener.position.end - size, end=closer.position.start + size)


def can_match_delimiters(opener: Delimiter, closer: Delimiter) -> bool:
    if opener.can_close or closer.can_open:
        open_length = opener.orig_length
        close_length = closer.orig_length
        return (open_length + close_length) % 3 != 0 or open_length % 3 == 0 and close_length % 3 == 0
    return True


def _neighbors(text: str, start: int, size: int) -> tuple[str, str]:
    previous = text[start - 1] if start > 0 else '\n'
    next_char = text[start + size] if start + size < len(text) else '\n'
    return previous, next_char


def _flanking(previous: str, next_char: str, cjk_friendly: bool = False) -> tuple[bool, bool]:
    prev_ws, next_ws = previous.isspace(), next_char.isspace()
    if cjk_friendly:
        prev_p, next_p = is_non_cjk_punctuation(previous), is_non_cjk_punctuation(next_char)
        prev_cjk = is_cjk_character(previous) or is_ideographic_variation_selector(previous)
        next_cjk = is_cjk_character(next_char)
        left = (not next_ws) and (not next_p or prev_ws or prev_p or prev_cjk)
        right = (not prev_ws) and (not prev_p or next_ws or next_p or next_cjk)
        return left, right

    prev_p, next_p = is_punctuation(previous), is_punctuation(next_char)
    left = (not next_ws) and (not next_p or prev_ws or prev_p)
    right = (not prev_ws) and (not prev_p or next_ws or next_p)
    return left, right


def can_open(text: str, start: int, size: int, marker: str, cjk_friendly: bool = False) -> bool:
    previous, next_char = _neighbors(text, start, size)
    left, right = _flanking(previous, next_char, cjk_friendly=cjk_friendly)
    if marker == '_':
        return left and (not right or is_punctuation(previous))
    return left


def can_close(text: str, start: int, size: int, marker: str, cjk_friendly: bool = False) -> bool:
    previous, next_char = _neighbors(text, start, size)
    left, right = _flanking(previous, next_char, cjk_friendly=cjk_friendly)
    if marker == '_':
        return right and (not left or is_punctuation(next_char))
    return right
