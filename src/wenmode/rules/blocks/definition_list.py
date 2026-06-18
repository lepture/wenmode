from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import DefinitionDescription, DefinitionTerm, Node
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

        children: list[Node] = create_terms(parser, lines, state)
        children.extend(parse_descriptions(parser, state))
        parse_following_items(parser, state, children)
        return DefinitionListNode(children=children)


def create_terms(parser: Parser, lines: list[str], state: BlockState) -> list[Node]:
    return [DefinitionTerm(children=parser.parse_inlines(line.strip(), state)) for line in lines if line.strip()]


def parse_descriptions(parser: Parser, state: BlockState) -> list[DefinitionDescription]:
    descriptions: list[DefinitionDescription] = []
    while not state.done:
        match = DESCRIPTION_RE.match(state.line)
        if match is None:
            break
        lines = [match.group('text') + line_ending(state.line)]
        state.advance()
        spread = collect_description_continuation(state, lines)
        children = parser.parse_blocks(''.join(lines), parent_state=state)
        descriptions.append(DefinitionDescription(children=children, spread=spread))
    return descriptions


def collect_description_continuation(state: BlockState, lines: list[str]) -> bool:
    spread = False
    while not state.done:
        if state.line.strip() == '':
            if not state.has(1) or INDENTED_RE.match(state.peek(1)) is None:
                break
            spread = True
            lines.append(state.line)
            state.advance()
            continue
        indented = INDENTED_RE.match(state.line)
        if indented is None:
            break
        lines.append(indented.group('text') + line_ending(state.line))
        state.advance()
    return spread


def parse_following_items(parser: Parser, state: BlockState, children: list[Node]) -> None:
    while not state.done:
        parsed = parse_following_terms(state)
        if parsed is None:
            return
        terms, next_index = parsed
        state.index = next_index
        children.extend(create_terms(parser, terms, state))
        children.extend(parse_descriptions(parser, state))


def parse_following_terms(state: BlockState) -> tuple[list[str], int] | None:
    index = state.index
    while state.has_index(index) and state.line_at(index).strip() == '':
        index += 1
    terms: list[str] = []
    while state.has_index(index):
        line = state.line_at(index)
        if line.strip() == '':
            return None
        if DESCRIPTION_RE.match(line) is not None:
            return (terms, index) if terms else None
        if line.startswith((' ', '\t')):
            return None
        terms.append(line)
        index += 1
    return None


def line_ending(line: str) -> str:
    return '\n' if line.endswith('\n') else ''
