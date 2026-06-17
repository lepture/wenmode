from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from wenmode.nodes import Abbreviation as AbbreviationNode
from wenmode.nodes import Node, Parent, Text
from wenmode.state import Abbreviation as AbbreviationDefinitionNode
from wenmode.state import BlockState

from .base import BlockRule, Rule

if TYPE_CHECKING:
    from wenmode.nodes import Root
    from wenmode.parser import Parser


ABBREVIATION_START_RE = re.compile(r'^[ \t]{0,3}\*\[(?P<label>[^\]\n]+)\]:[ \t]*(?P<title>.*)$')
ABBREVIATION_CONTINUATION_RE = re.compile(r'^(?: {3,}|\t)(?P<title>.*)$')


class Abbreviation(Rule):
    def __init__(self) -> None:
        super().__init__('abbreviation')
        self.root_transforms = [AbbreviationTransform()]


class AbbreviationDefinition(BlockRule):
    order = 80

    def __init__(self) -> None:
        super().__init__('abbreviation_definition', r'[ \t]{0,3}\*\[')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> None:
        parsed = parse_abbreviation_definition(state, state.index)
        if parsed is None:
            return None

        next_index, label, title = parsed
        state.abbreviations[label] = AbbreviationDefinitionNode(label=label, title=title)
        state.index = next_index
        return None


class AbbreviationTransform:
    name = 'abbreviation'
    defer_inlines = True
    required_rules: Sequence[type[Rule] | Rule] = [AbbreviationDefinition]

    def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
        pass

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        if not state.abbreviations:
            return
        pattern = re.compile('|'.join(re.escape(label) for label in sorted(state.abbreviations, key=len, reverse=True)))
        transform_abbreviations(root, state, pattern)


def parse_abbreviation_definition(state: BlockState, index: int) -> tuple[int, str, str] | None:
    match = ABBREVIATION_START_RE.match(state.line_at(index).rstrip('\r\n'))
    if match is None:
        return None

    label = match.group('label')
    title_lines = [match.group('title')]
    index += 1
    if title_lines[0] == '':
        while state.has_index(index):
            continuation = ABBREVIATION_CONTINUATION_RE.match(state.line_at(index).rstrip('\r\n'))
            if continuation is None:
                break
            title_lines.append(continuation.group('title'))
            index += 1

    return index, label, '\n'.join(title_lines).strip()


def transform_abbreviations(node: Parent, state: BlockState, pattern: re.Pattern[str]) -> None:
    children: list[Node] = []
    changed = False
    for child in node.children:
        if isinstance(child, Text):
            replaced = replace_abbreviations(child, state, pattern)
            children.extend(replaced)
            changed = changed or replaced != [child]
        else:
            if isinstance(child, Parent):
                transform_abbreviations(child, state, pattern)
            children.append(child)
    if changed:
        node.children = children


def replace_abbreviations(node: Text, state: BlockState, pattern: re.Pattern[str]) -> list[Node]:
    nodes: list[Node] = []
    pos = 0
    for match in pattern.finditer(node.value):
        if match.start() > pos:
            nodes.append(Text(value=node.value[pos : match.start()], _parse_emphasis=node._parse_emphasis))
        label = match.group(0)
        definition = state.get_abbreviation(label)
        if definition is None:
            nodes.append(Text(value=label, _parse_emphasis=node._parse_emphasis))
        else:
            nodes.append(AbbreviationNode(title=definition.title, children=[Text(value=label, _parse_emphasis=False)]))
        pos = match.end()
    if not nodes:
        return [node]
    if pos < len(node.value):
        nodes.append(Text(value=node.value[pos:], _parse_emphasis=node._parse_emphasis))
    return nodes
