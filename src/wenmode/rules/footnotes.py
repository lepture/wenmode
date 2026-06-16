from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import FootnoteDefinition as FootnoteDefinitionNode
from wenmode.nodes import FootnoteReference, Node
from wenmode.rules.base import BlockRule, InlineRule
from wenmode.state import Footnote as FootnoteState
from wenmode.utils import count_indent, normalize_label, normalize_label_text

if TYPE_CHECKING:
    from wenmode.parser import Wenmode
    from wenmode.state import BlockState


FOOTNOTE_DEFINITION_RE = re.compile(
    r'^[ \t]{0,3}\[\^(?P<label>(?:\\.|[^\[\]\\\n]){1,999})\]:[ \t]*(?P<rest>.*)$'
)
FOOTNOTE_REFERENCE_RE = r'\[\^(?P<label>(?:\\.|[^\[\]\\\n]){1,999})]'


class Footnote(InlineRule):
    has_footnotes = True

    def __init__(self) -> None:
        super().__init__('footnote', FOOTNOTE_REFERENCE_RE, '[')

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        if state is None:
            return None, match.start()

        identifier = normalize_label(match.group('label'))
        footnote = state.get_footnote(identifier)
        if footnote is None:
            return None, match.start()

        return FootnoteReference(identifier=footnote.identifier, label=footnote.label), match.end()


class FootnoteDefinition(BlockRule):
    def __init__(self) -> None:
        super().__init__('footnote_definition', r'[ \t]{0,3}\[\^')

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> FootnoteDefinitionNode | None:
        parsed = FOOTNOTE_DEFINITION_RE.match(state.line.rstrip('\r\n'))
        if parsed is None:
            return None

        label = normalize_label_text(parsed.group('label'))
        identifier = normalize_label(label)
        if identifier == '':
            return None

        content_lines = collect_definition_lines(state, parsed.group('rest'))
        children = parser.parse_blocks(''.join(content_lines), parent_state=state) if content_lines else []
        node = FootnoteDefinitionNode(identifier=identifier, label=label, children=children)
        state.footnotes.setdefault(identifier, FootnoteState(identifier=identifier, label=label, children=children))
        return node


def collect_definition_lines(state: BlockState, rest: str) -> list[str]:
    lines: list[str] = []
    if rest:
        lines.append(rest + '\n')
    state.advance()

    while not state.done:
        line = state.line
        if line.strip() == '':
            if has_later_continuation(state):
                lines.append('\n')
                state.advance()
                continue
            break
        if count_indent(line) < 2:
            break
        lines.append(strip_indent(line, 2))
        state.advance()

    return lines


def has_later_continuation(state: BlockState) -> bool:
    index = state.index + 1
    while index < len(state.lines):
        line = state.lines[index]
        if line.strip() == '':
            index += 1
            continue
        return count_indent(line) >= 2
    return False


def strip_indent(line: str, columns: int) -> str:
    column = 0
    index = 0
    while index < len(line) and column < columns:
        char = line[index]
        if char == ' ':
            column += 1
            index += 1
        elif char == '\t':
            column += 4 - column % 4
            index += 1
        else:
            break
    return line[index:]
