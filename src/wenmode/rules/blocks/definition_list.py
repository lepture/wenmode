from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import DefinitionDescription, DefinitionTerm, Node, Point
from wenmode.nodes import DefinitionList as DefinitionListNode
from wenmode.state import BlockState

from ..base import ContinueRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


DESCRIPTION_RE = re.compile(r'^[ \t]{0,3}:[ \t]+(?P<text>.*)$')
INDENTED_RE = re.compile(r'^(?: {4}|\t)(?P<text>.*)$')


class DefinitionList(ContinueRule):
    """Parse colon-prefixed definition list continuations.

    Markdown syntax:

    .. code-block:: markdown

       Term
       : Definition
    """

    def __init__(self) -> None:
        super().__init__('definition_list')

    def matches(self, line: str) -> bool:
        return line.lstrip(' \t').startswith(':')

    def parse_paragraph_continuation(
        self, parser: Parser, state: BlockState, lines: list[str]
    ) -> DefinitionListNode | None:
        if DESCRIPTION_RE.match(state.line) is None:
            return None

        term_start_index = state.index - len(lines)
        children: list[Node] = create_terms(parser, lines, state, term_start_index)
        children.extend(parse_descriptions(parser, state))
        parse_following_items(parser, state, children)
        return DefinitionListNode(children=children)


def create_terms(parser: Parser, lines: list[str], state: BlockState, start_index: int) -> list[Node]:
    terms: list[Node] = []
    for offset, line in enumerate(lines):
        if not line.strip():
            continue
        text = line.strip()
        leading = len(line) - len(line.lstrip())
        point = state.point_at_line_offset(start_index + offset, leading)
        term = DefinitionTerm(
            children=parser.parse_inlines(text, state, source=parser.source_map_for_text(text, point))
        )
        if parser.positions:
            term.position = state.position_between(start_index + offset, start_index + offset + 1)
        terms.append(term)
    return terms


def parse_descriptions(parser: Parser, state: BlockState) -> list[DefinitionDescription]:
    descriptions: list[DefinitionDescription] = []
    while not state.done:
        match = DESCRIPTION_RE.match(state.line)
        if match is None:
            break
        start_index = state.index
        text = match.group('text') + line_ending(state.line)
        lines = [text]
        source_parts: list[tuple[str, Point]] = []
        point = state.point_at_line_offset(state.index, match.start('text'))
        if point is not None:
            source_parts.append((text, point))
        state.advance()
        spread = collect_description_continuation(state, lines, source_parts)
        children = parser.parse_blocks(
            ''.join(lines),
            parent_state=state,
            source=parser.source_map_from_parts(source_parts),
        )
        description = DefinitionDescription(children=children, spread=spread)
        if parser.positions:
            description.position = state.position_between(start_index, state.index)
        descriptions.append(description)
    return descriptions


def collect_description_continuation(
    state: BlockState, lines: list[str], source_parts: list[tuple[str, Point]]
) -> bool:
    spread = False
    while not state.done:
        if state.line.strip() == '':
            if not state.has(1) or INDENTED_RE.match(state.peek(1)) is None:
                break
            spread = True
            lines.append(state.line)
            point = state.point_at_line_offset(state.index, 0)
            if point is not None:
                source_parts.append((state.line, point))
            state.advance()
            continue
        indented = INDENTED_RE.match(state.line)
        if indented is None:
            break
        text = indented.group('text') + line_ending(state.line)
        lines.append(text)
        point = state.point_at_line_offset(state.index, indented.start('text'))
        if point is not None:
            source_parts.append((text, point))
        state.advance()
    return spread


def parse_following_items(parser: Parser, state: BlockState, children: list[Node]) -> None:
    while not state.done:
        parsed = parse_following_terms(state)
        if parsed is None:
            return
        terms, term_start_index, next_index = parsed
        state.index = next_index
        children.extend(create_terms(parser, terms, state, term_start_index))
        children.extend(parse_descriptions(parser, state))


def parse_following_terms(state: BlockState) -> tuple[list[str], int, int] | None:
    index = state.index
    while state.has_index(index) and state.line_at(index).strip() == '':
        index += 1
    start_index = index
    terms: list[str] = []
    while state.has_index(index):
        line = state.line_at(index)
        if line.strip() == '':
            return None
        if DESCRIPTION_RE.match(line) is not None:
            return (terms, start_index, index) if terms else None
        if line.startswith((' ', '\t')):
            return None
        terms.append(line)
        index += 1
    return None


def line_ending(line: str) -> str:
    return '\n' if line.endswith('\n') else ''
