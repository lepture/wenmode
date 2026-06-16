from __future__ import annotations

import re
import string
from collections.abc import Iterable
from typing import Any, TypeVar

from .nodes import Node, Paragraph, Root, Text
from .rules.base import BlockRule, InlineRule, Rule
from .rules.blocks.html import is_html_block_tag
from .rules.footnotes import FootnoteDefinition
from .rules.inlines.emphasis import parse_emphasis_sequence
from .rules.references import ReferenceDefinition
from .state import BlockState

LIST_MARKER_RE = re.compile(
    r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?P<spaces>[ \t]+|$)(?P<rest>.*)$'
)
HTML_TAG_START_RE = re.compile(r'</?[A-Za-z]')
HTML_PARAGRAPH_INTERRUPT_RE = re.compile(r'(?i)<(?:script|pre|style|textarea)(?:\s|>|$)')
PUNCTUATION = set(string.punctuation)
T = TypeVar('T', bound=Rule)


class Wenmode:
    max_container_depth = 100

    def __init__(self, rules: Iterable[type[Any] | Rule]) -> None:
        resolved_rules: list[Rule] = [rule() if isinstance(rule, type) else rule for rule in rules]
        if any(rule.has_references for rule in resolved_rules):
            resolved_rules.append(ReferenceDefinition())
        if any(rule.has_footnotes for rule in resolved_rules):
            resolved_rules.append(FootnoteDefinition())
        self.rules = {rule.name: rule for rule in resolved_rules}
        self.block_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, BlockRule)])
        self.inline_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, InlineRule)])
        self._emphasis_enabled = 'emphasis' in self.rules
        self._inline_rule_order = {rule.name: index for index, rule in enumerate(self.inline_rules)}
        self._triggered_inline_rules, self._search_inline_rules = self._prepare_inline_dispatch(self.inline_rules)
        self._inline_trigger_re = self._compile_inline_trigger_re(self._triggered_inline_rules)
        self._block_openers = self._compile_block_openers(self.block_rules)

    def parse(self, text: str) -> Root:
        return Root(children=self.parse_blocks(text))

    def parse_blocks(self, text: str, parent_state: BlockState | None = None) -> list[Node]:
        references = parent_state.references if parent_state is not None else {}
        footnotes = parent_state.footnotes if parent_state is not None else {}
        state = BlockState.from_text(
            text,
            references=references,
            footnotes=footnotes,
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

            if self._is_plain_paragraph_start(state.line):
                children.append(self._parse_paragraph(state))
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

        while pos < len(text):
            found = self._find_inline_match(text, pos)

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
        if self._emphasis_enabled and contains_emphasis_marker(nodes):
            nodes = parse_emphasis_nodes(nodes)
        return merge_text(nodes)

    def _find_inline_match(self, text: str, pos: int) -> tuple[int, InlineRule, re.Match[str]] | None:
        found = self._find_search_inline_match(text, pos)
        limit = found[0] if found is not None else len(text)
        if self._inline_trigger_re is None:
            return found

        trigger_match = self._inline_trigger_re.search(text, pos)
        while trigger_match is not None and trigger_match.start() <= limit:
            start = trigger_match.start()
            for rule in self._triggered_inline_rules[text[start]]:
                match = rule.compiled.match(text, start)
                if match is None:
                    continue
                candidate = (start, rule, match)
                if found is None or self._inline_candidate_before(candidate, found):
                    return candidate
            trigger_match = self._inline_trigger_re.search(text, start + 1)
        return found

    def _find_search_inline_match(self, text: str, pos: int) -> tuple[int, InlineRule, re.Match[str]] | None:
        found: tuple[int, InlineRule, re.Match[str]] | None = None
        for rule in self._search_inline_rules:
            match = rule.compiled.search(text, pos)
            if match is None:
                continue
            candidate = (match.start(), rule, match)
            if found is None or self._inline_candidate_before(candidate, found):
                found = candidate
        return found

    def _inline_candidate_before(
        self, candidate: tuple[int, InlineRule, re.Match[str]], current: tuple[int, InlineRule, re.Match[str]]
    ) -> bool:
        if candidate[0] != current[0]:
            return candidate[0] < current[0]
        return self._inline_rule_order[candidate[1].name] < self._inline_rule_order[current[1].name]

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

    def _is_plain_paragraph_start(self, line: str) -> bool:
        if 'table' in self.rules and '|' in line:
            return False
        char = line[0]
        return not char.isspace() and not char.isdigit() and char not in PUNCTUATION

    @staticmethod
    def _compile_block_openers(rules: list[BlockRule]) -> re.Pattern[str] | None:
        patterns = [f'(?P<{rule.name}>{rule.pattern})' for rule in rules]
        return re.compile('|'.join(patterns)) if patterns else None

    @staticmethod
    def _prepare_inline_dispatch(
        rules: list[InlineRule],
    ) -> tuple[dict[str, list[InlineRule]], list[InlineRule]]:
        triggered: dict[str, list[InlineRule]] = {}
        search: list[InlineRule] = []
        for rule in rules:
            if rule.name == 'emphasis':
                continue
            if not rule.trigger_chars:
                search.append(rule)
                continue
            for char in rule.trigger_chars:
                triggered.setdefault(char, []).append(rule)
        return triggered, search

    @staticmethod
    def _compile_inline_trigger_re(rules: dict[str, list[InlineRule]]) -> re.Pattern[str] | None:
        if not rules:
            return None
        return re.compile(f'[{re.escape("".join(rules))}]')


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


def contains_emphasis_marker(nodes: list[Node]) -> bool:
    for node in nodes:
        if isinstance(node, Text) and node._parse_emphasis and ('*' in node.value or '_' in node.value):
            return True
    return False


def sorted_by_order(rules: list[T]) -> list[T]:
    return [rule for _, rule in sorted(enumerate(rules), key=lambda item: (item[1].order, item[0]))]
