from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .nodes import Node, Paragraph, Root, Text
from .rules.base import BlockRule, InlineRule, Rule
from .rules.blocks.html import is_html_block_tag
from .rules.inlines.emphasis import parse_emphasis_sequence
from .rules.references import ReferenceDefinition
from .state import BlockState

LIST_MARKER_RE = re.compile(
    r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?P<spaces>[ \t]+|$)(?P<rest>.*)$'
)
HTML_TAG_START_RE = re.compile(r'</?[A-Za-z]')
HTML_PARAGRAPH_INTERRUPT_RE = re.compile(r'(?i)<(?:script|pre|style|textarea)(?:\s|>|$)')


class Wenmode:
    max_container_depth = 100

    def __init__(self, rules: Iterable[type[Any] | Rule]) -> None:
        rules = [rule() if isinstance(rule, type) else rule for rule in rules]
        if any(rule.has_references for rule in rules):
            rules.append(ReferenceDefinition())
        self.rules = {rule.name: rule for rule in rules}
        self.block_rules = [rule for rule in rules if isinstance(rule, BlockRule)]
        self.inline_rules = [rule for rule in rules if isinstance(rule, InlineRule)]
        self._block_openers = self._compile_block_openers(self.block_rules)

    def parse(self, text: str) -> Root:
        return Root(children=self.parse_blocks(text))

    def parse_blocks(self, text: str, parent_state: BlockState | None = None) -> list[Node]:
        references = parent_state.references if parent_state is not None else {}
        state = BlockState.from_text(
            text,
            references=references,
            depth=(parent_state.depth + 1 if parent_state else 0),
            pending_inlines=parent_state.pending_inlines if parent_state is not None else None,
            pending_inline_callbacks=parent_state.pending_inline_callbacks if parent_state is not None else None,
            defer_inlines=True,
        )
        children: list[Node] = []

        while not state.done:
            if state.line.strip() == '':
                state.advance()
                continue

            match = self._block_openers.match(state.line) if self._block_openers else None
            if match is not None and not self._container_depth_exceeded(match, state):
                rule = self._match_block_rule(match)
                previous_index = state.index
                parsed = rule.parse(self, state, match)
                if parsed is not None:
                    children.append(parsed)
                    continue
                if state.index != previous_index:
                    continue

            children.append(self._parse_paragraph(state))

        if parent_state is None:
            self._resolve_pending_inlines(state)
        return children

    def parse_inlines(self, text: str, state: BlockState | None = None) -> list[Node]:
        if state is not None and state.defer_inlines:
            pending_nodes: list[Node] = []
            state.pending_inlines.append((pending_nodes, text))
            return pending_nodes

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

    def _resolve_pending_inlines(self, state: BlockState) -> None:
        state.defer_inlines = False
        pending = list(state.pending_inlines)
        state.pending_inlines.clear()
        for nodes, text in pending:
            nodes[:] = self.parse_inlines(text, state)
        callbacks = list(state.pending_inline_callbacks)
        state.pending_inline_callbacks.clear()
        for callback in callbacks:
            callback()

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
        if match.lastgroup == 'reference_definition':
            return False
        if match.lastgroup == 'list':
            marker = LIST_MARKER_RE.match(line.rstrip('\r\n'))
            if marker is not None and marker.group('rest').strip() == '':
                return False
            if marker is not None and marker.group('ordered') is not None and marker.group('ordered') != '1':
                return False
        if match.lastgroup == 'html_block':
            stripped = line.lstrip(' \t')
            if is_html_block_tag(stripped):
                return True
            if HTML_TAG_START_RE.match(stripped) and not HTML_PARAGRAPH_INTERRUPT_RE.match(stripped):
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
