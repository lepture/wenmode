from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import FootnoteDefinition as FootnoteDefinitionNode
from wenmode.nodes import FootnoteReference, Node, Root
from wenmode.state import FOOTNOTES
from wenmode.state import Footnote as FootnoteState
from wenmode.utils import count_indent, normalize_label, normalize_label_text

from .base import BlockRule, InlineRule, Rule

if TYPE_CHECKING:
    from wenmode.parser import Parser
    from wenmode.state import BlockState


FOOTNOTE_DEFINITION_RE = re.compile(
    r'^[ \t]{0,3}\[\^(?P<label>(?:\\[^\s]|[^\s\[\]\\]){1,999})\]:[ \t]*(?P<rest>.*)$'
)
FOOTNOTE_REFERENCE_RE = r'\[\^(?P<label>(?:\\[^\s]|[^\s\[\]\\]){1,999})]'


class Footnote(InlineRule):
    order: ClassVar[int] = 50

    def __init__(self) -> None:
        super().__init__('footnote', FOOTNOTE_REFERENCE_RE, '[')
        self.root_transforms = [FootnoteTransform()]

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        if state is None:
            return None, match.start()

        identifier = normalize_label(match.group('label'))
        footnote = state.store.get(FOOTNOTES).get(identifier)
        if footnote is None:
            return None, match.start()

        return FootnoteReference(identifier=footnote.identifier, label=footnote.label), match.end()


class FootnoteDefinition(BlockRule):
    def __init__(self) -> None:
        super().__init__('footnote_definition', r'[ \t]{0,3}\[\^')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> FootnoteDefinitionNode | None:
        parsed = FOOTNOTE_DEFINITION_RE.match(state.line.rstrip('\r\n'))
        if parsed is None:
            return None

        label = normalize_label_text(parsed.group('label'))
        identifier = normalize_label(label)
        if identifier == '':
            return None

        content_lines = collect_definition_lines(state, parsed.group('rest'))
        children = parser.parse_blocks(''.join(content_lines), parent_state=state) if content_lines else []
        return FootnoteDefinitionNode(identifier=identifier, label=label, children=children)


class FootnoteTransform:
    name = 'footnote'
    defer_inlines = True
    required_rules: Sequence[type[Rule] | Rule] = [FootnoteDefinition]

    def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
        footnotes = state.store.get(FOOTNOTES)
        for identifier, definition in collect_footnote_definitions(root).items():
            footnotes.setdefault(
                identifier,
                FootnoteState(identifier=identifier, label=definition.label, children=definition.children),
            )

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        root.footnote_definitions = collect_footnote_definitions(root)


def collect_footnote_definitions(node: Node) -> dict[str, FootnoteDefinitionNode]:
    definitions: dict[str, FootnoteDefinitionNode] = {}
    collect_footnote_definitions_into(node, definitions)
    return definitions


def collect_footnote_definitions_into(node: Node, definitions: dict[str, FootnoteDefinitionNode]) -> None:
    if isinstance(node, FootnoteDefinitionNode):
        definitions.setdefault(node.identifier, node)
    children = getattr(node, 'children', None)
    if isinstance(children, list):
        for child in children:
            collect_footnote_definitions_into(child, definitions)


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
    offset = 1
    while state.has(offset):
        line = state.peek(offset)
        if line.strip() == '':
            offset += 1
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
