from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import FootnoteDefinition as FootnoteDefinitionNode
from wenmode.nodes import FootnoteReference, Node, Root
from wenmode.utils import count_indent, normalize_label, normalize_label_text

from .._parser.source import SourceCollector
from .._parser.store import StateKey
from .base import BlockCandidate, BlockRule, InlineCandidate, InlineRule
from .transforms import RootTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser

    from .._parser.state import BlockState


FOOTNOTE_DEFINITION_RE = re.compile(r'^[ \t]{0,3}\[\^(?P<label>(?:\\\S|[^\s\[\]\\]){1,999})\]:[ \t]*')
FOOTNOTE_REFERENCE_RE = r'\[\^(?P<label>(?:\\[^\s]|[^\s\[\]\\]){1,999})]'


@dataclass
class FootnoteState:
    identifier: str
    label: str
    children: list[Node]


FootnoteCache = dict[str, FootnoteState]
FootnoteDefinitionCache = dict[str, FootnoteDefinitionNode]
FOOTNOTES_KEY = StateKey[FootnoteCache]('wenmode.footnotes', lambda: {})
FOOTNOTE_DEFINITIONS_KEY = StateKey[FootnoteDefinitionCache]('wenmode.footnote_definitions', lambda: {})


class Footnote(InlineRule):
    """Parse footnote references and collect matching definitions.

    Markdown syntax:

    .. code-block:: markdown

       A note[^a].

       [^a]: Footnote text.
    """

    order: ClassVar[int] = 50
    name = 'footnote'
    pattern = FOOTNOTE_REFERENCE_RE
    opener = '['

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        match = candidate.match
        assert match is not None
        identifier = normalize_label(match.group('label'))
        footnote = state.store.get(FOOTNOTES_KEY).get(identifier)
        if footnote is None:
            return None, candidate.start

        return FootnoteReference(identifier=footnote.identifier, label=footnote.label), match.end()


class FootnoteDefinition(BlockRule):
    """Parse footnote definition blocks.

    Markdown syntax:

    .. code-block:: markdown

       [^a]: Footnote text.
    """

    name = 'footnote_definition'
    pattern = r'[ \t]{0,3}\[\^'

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> FootnoteDefinitionNode | None:
        line = state.line.rstrip('\r\n')
        parsed = FOOTNOTE_DEFINITION_RE.match(line)
        if parsed is None:
            return None

        label = normalize_label_text(parsed.group('label'))
        identifier = normalize_label(label)
        if identifier == '':
            return None

        source = state.source.collect()
        rest_start = parsed.end()
        content_lines = collect_definition_lines(state, rest_start, line[rest_start:], source)
        if content_lines:
            children = parser.parse_blocks(''.join(content_lines), parent_state=state, source=source.map())
        else:
            children = []
        return FootnoteDefinitionNode(identifier=identifier, label=label, children=children)


class FootnoteTransform(RootTransform):
    name = 'footnote'
    defer_inlines = True

    def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
        definitions = collect_footnote_definitions(root)
        state.store.get(FOOTNOTE_DEFINITIONS_KEY).update(definitions)

        footnotes = state.store.get(FOOTNOTES_KEY)
        for identifier, definition in definitions.items():
            footnotes.setdefault(
                identifier, FootnoteState(identifier=identifier, label=definition.label, children=definition.children)
            )

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        root.footnote_definitions = state.store.get(FOOTNOTE_DEFINITIONS_KEY)


Footnote.required_rules = [FootnoteDefinition]
Footnote.root_transforms = [FootnoteTransform()]


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


def collect_definition_lines(state: BlockState, rest_start: int, rest: str, source: SourceCollector) -> list[str]:
    lines: list[str] = []
    if rest:
        text = rest + '\n'
        lines.append(text)
        source.add(state.index, rest_start, text)
    state.advance()

    while not state.done:
        line = state.line
        if line.strip() == '':
            if collect_blank_continuations(state, lines, source):
                continue
            break
        if count_indent(line) < 2:
            break
        offset = indent_offset(line, 2)
        text = line[offset:]
        lines.append(text)
        source.add(state.index, offset, text)
        state.advance()

    return lines


def collect_blank_continuations(state: BlockState, lines: list[str], source: SourceCollector) -> bool:
    cursor = state.index
    while state.has_index(cursor):
        line = state.line_at(cursor)
        if line.strip() == '':
            cursor += 1
            continue
        if count_indent(line) < 2:
            return False
        while state.index < cursor:
            lines.append('\n')
            source.add(state.index, 0, '\n')
            state.advance()
        return True
    return False


def strip_indent(line: str, columns: int) -> str:
    return line[indent_offset(line, columns) :]


def indent_offset(line: str, columns: int) -> int:
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
    return index
