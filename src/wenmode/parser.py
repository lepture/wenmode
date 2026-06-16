from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .nodes import Node, Paragraph, Root, Text
from .rules.base import BlockRule, InlineRule, Rule
from .rules.inlines.emphasis import parse_emphasis_sequence
from .rules.references import extract_references
from .state import BlockState, Reference


class Wenmode:
    max_container_depth = 100

    def __init__(self, rules: Iterable[type[Any] | Rule]) -> None:
        rules = [rule() if isinstance(rule, type) else rule for rule in rules]
        self.rules = {rule.name: rule for rule in rules}
        self.block_rules = [rule for rule in rules if isinstance(rule, BlockRule)]
        self.inline_rules = [rule for rule in rules if isinstance(rule, InlineRule)]
        self._has_references = any(rule.has_references for rule in rules)
        self._block_openers = self._compile_block_openers(self.block_rules)

    def parse(self, text: str) -> Root:
        return Root(children=self.parse_blocks(text))

    def parse_blocks(self, text: str, parent_state: BlockState | None = None) -> list[Node]:
        references = parent_state.references if parent_state is not None else {}
        if self._has_references:
            text, extracted = extract_references(text, self)
            for label, reference in extracted.items():
                references.setdefault(label, reference)
        state = BlockState.from_text(text, references=references, depth=(parent_state.depth + 1 if parent_state else 0))
        children: list[Node] = []

        while not state.done:
            if state.line.strip() == '':
                state.advance()
                continue

            match = self._block_openers.match(state.line) if self._block_openers else None
            if match is not None and not self._container_depth_exceeded(match, state):
                rule = self._match_block_rule(match)
                parsed = rule.parse(self, state, match)
                if parsed is not None:
                    children.append(parsed)
                continue

            children.append(self._parse_paragraph(state))

        return children

    def parse_inlines(self, text: str, state: BlockState | None = None) -> list[Node]:
        nodes: list[Node] = []
        pos = 0
        emphasis_enabled = 'emphasis' in self.rules
        inline_rules = [rule for rule in self.inline_rules if rule.name != 'emphasis']

        while pos < len(text):
            found: tuple[int, InlineRule, re.Match[str]] | None = None
            for rule in inline_rules:
                match = rule.compiled.search(text, pos)
                if match is None:
                    continue
                if found is None or match.start() < found[0]:
                    found = (match.start(), rule, match)

            if found is None:
                nodes.append(Text(value=text[pos:]))
                break

            start, rule, match = found
            if start > pos:
                nodes.append(Text(value=text[pos:start]))

            node, end = rule.parse(self, text, match, state)
            if node is None or end <= start:
                nodes.append(Text(value=text[start : start + 1]))
                pos = start + 1
            else:
                nodes.append(node)
                pos = end

        nodes = merge_text(nodes)
        if emphasis_enabled:
            nodes = parse_emphasis_nodes(nodes)
        return merge_text(nodes)

    def _parse_paragraph(self, state: BlockState) -> Node:
        lines: list[str] = []
        while not state.done and state.line.strip() != '':
            if lines:
                setext_heading = self.rules.get('setext_heading')
                if setext_heading is not None:
                    parsed = setext_heading.parse_paragraph_continuation(self, state, lines)
                    if parsed is not None:
                        return parsed
            if lines and self.is_paragraph_interrupt(state.line, state):
                break
            lines.append(state.line.lstrip(' \t') if lines else state.line)
            state.advance()

        text = ''.join(lines).strip()
        return Paragraph(children=self.parse_inlines(text, state))

    def _match_block_rule(self, match: re.Match[str]) -> BlockRule:
        group = match.lastgroup
        if group is None:
            raise RuntimeError('block opener matched without a named group')
        rule = self.rules.get(group)
        if isinstance(rule, BlockRule):
            return rule
        raise RuntimeError(f'unknown block rule: {group}')

    def is_paragraph_interrupt(self, line: str, state: BlockState | None = None) -> bool:
        if self._block_openers is None:
            return False
        match = self._block_openers.match(line)
        if match is None:
            return False
        if self._container_depth_exceeded(match, state):
            return False
        if match.lastgroup == 'list':
            marker = re.match(
                r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?P<spaces>[ \t]+|$)(?P<rest>.*)$',
                line.rstrip('\r\n'),
            )
            if marker is not None and marker.group('rest').strip() == '':
                return False
            if marker is not None and marker.group('ordered') is not None and marker.group('ordered') != '1':
                return False
        if match.lastgroup == 'html_block':
            stripped = line.lstrip(' \t')
            if is_block_html_start(stripped):
                return True
            if re.match(r'</?[A-Za-z]', stripped) and not re.match(
                r'(?i)<(?:script|pre|style|textarea)(?:\s|>|$)', stripped
            ):
                return False
        return match.lastgroup != 'indented_code'

    def _container_depth_exceeded(self, match: re.Match[str], state: BlockState | None) -> bool:
        if match.lastgroup not in {'blockquote', 'list'} or state is None:
            return False
        return state.depth >= self.max_container_depth

    @staticmethod
    def _compile_block_openers(rules: list[BlockRule]) -> re.Pattern[str] | None:
        patterns = [f'(?P<{rule.name}>{rule.pattern})' for rule in rules]
        return re.compile('|'.join(patterns)) if patterns else None


def merge_text(nodes: list[Node]) -> list[Node]:
    merged: list[Node] = []
    for node in nodes:
        if (
            isinstance(node, Text)
            and merged
            and isinstance(merged[-1], Text)
            and node._parse_emphasis == merged[-1]._parse_emphasis
        ):
            merged[-1].value += node.value
        else:
            merged.append(node)
    return merged


def parse_emphasis_nodes(nodes: list[Node]) -> list[Node]:
    return parse_emphasis_sequence(nodes)


def is_block_html_start(line: str) -> bool:
    return re.match(
        r'(?i)</?(?:address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h1|h2|h3|h4|h5|h6|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?:\s|/?>|$)',
        line,
    ) is not None
