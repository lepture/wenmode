from __future__ import annotations

import re
import string
from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar, cast

from .nodes import Node, Paragraph, Root, Text
from .rules.base import BlockRule, ContinueRule, InlineRule, Rule
from .rules.blocks.html import is_html_block_tag
from .rules.inlines.emphasis import parse_emphasis_sequence
from .rules.transforms import RootTransform
from .state import BlockState, LineSource, StreamBlockState, StreamLineBuffer

LIST_MARKER_RE = re.compile(
    r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?P<spaces>[ \t]+|$)(?P<rest>.*)$'
)
HTML_TAG_START_RE = re.compile(r'</?[A-Za-z]')
HTML_PARAGRAPH_INTERRUPT_RE = re.compile(r'(?i)<(?:script|pre|style|textarea)(?:\s|>|$)')
PUNCTUATION = set(string.punctuation)
T = TypeVar('T', bound=Rule)
InlineSearchCache = dict[str, object]


class StreamingUnsupportedError(ValueError):
    pass


class Parser:
    max_container_depth = 20

    def __init__(self, rules: Iterable[type[Rule] | Rule]) -> None:
        self._registered_rules: list[Rule] = []
        self.register_rules(rules)

    def register_rule(self, rule: type[Rule] | Rule) -> None:
        self._register_resolved_rule(self._resolve_rule(rule))
        self._rebuild_rules()

    def register_rules(self, rules: Iterable[type[Rule] | Rule]) -> None:
        for rule in rules:
            self._register_resolved_rule(self._resolve_rule(rule))
        self._rebuild_rules()

    def _register_resolved_rule(self, rule: Rule) -> None:
        for index, registered in enumerate(self._registered_rules):
            if registered.name == rule.name:
                self._registered_rules[index] = rule
                return
        self._registered_rules.append(rule)

    @staticmethod
    def _resolve_rule(rule: type[Rule] | Rule) -> Rule:
        return cast(Callable[[], Rule], rule)() if isinstance(rule, type) else rule

    def _rebuild_rules(self) -> None:
        resolved_rules = list(self._registered_rules)
        root_transforms = self._collect_root_transforms(resolved_rules)
        for transform in root_transforms:
            for required in transform.required_rules:
                rule = self._resolve_rule(required)
                if all(registered.name != rule.name for registered in resolved_rules):
                    resolved_rules.append(rule)

        self.rules = {rule.name: rule for rule in resolved_rules}
        self.block_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, BlockRule)])
        self.inline_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, InlineRule)])
        self.root_transforms = root_transforms
        self._paragraph_continuations = [
            rule.parse_paragraph_continuation for rule in resolved_rules if isinstance(rule, ContinueRule)
        ]
        self._emphasis_enabled = 'emphasis' in self.rules
        self._defer_inlines = any(transform.defer_inlines for transform in root_transforms)
        self._inline_rule_order = {rule.name: index for index, rule in enumerate(self.inline_rules)}
        self._triggered_inline_rules, self._search_inline_rules = self._prepare_inline_dispatch(self.inline_rules)
        self._inline_trigger_re = self._compile_inline_trigger_re(self._triggered_inline_rules)
        self._block_openers = self._compile_block_openers(self.block_rules)

    def parse(self, source: LineSource) -> Root:
        state = self._create_block_state(source, defer_inlines=self._defer_inlines)
        root = Root(children=self._parse_block_nodes(state))
        for transform in self.root_transforms:
            transform.prepare(self, root, state)
        self._resolve_pending_inlines(state)
        for transform in self.root_transforms:
            transform.transform(self, root, state)
        return root

    def parse_iter(self, source: LineSource) -> Iterator[Node]:
        self._assert_streaming_supported()
        state = self._create_block_state(source, defer_inlines=False)
        while not state.done:
            node = self._parse_next_block_node(state)
            if node is not None:
                yield node

    def parse_blocks(self, text: str, parent_state: BlockState) -> list[Node]:
        state = BlockState(
            text.splitlines(keepends=True),
            references=parent_state.references,
            footnotes=parent_state.footnotes,
            abbreviations=parent_state.abbreviations,
            depth=parent_state.depth + 1,
            pending_inlines=parent_state.pending_inlines,
            pending_inline_callbacks=parent_state.pending_inline_callbacks,
            inline_cache=parent_state.inline_cache,
            defer_inlines=parent_state.defer_inlines,
        )
        return self._parse_block_nodes(state)

    def _create_block_state(self, source: LineSource, defer_inlines: bool) -> BlockState:
        if isinstance(source, str):
            return BlockState(source.splitlines(keepends=True), defer_inlines=defer_inlines)
        return StreamBlockState(StreamLineBuffer(source), defer_inlines=defer_inlines)

    def _parse_block_nodes(self, state: BlockState) -> list[Node]:
        children: list[Node] = []

        while not state.done:
            node = self._parse_next_block_node(state)
            if node is not None:
                children.append(node)

        return children

    def _parse_next_block_node(self, state: BlockState) -> Node | None:
        while not state.done:
            line = state.line
            if line.strip() == '':
                state.advance()
                continue

            if self._is_plain_paragraph_start(line):
                return self._parse_paragraph(state)

            match = self._block_openers.match(line) if self._block_openers else None
            if match is not None and not self._container_depth_exceeded(match, state):
                rule = self._match_block_rule(match)
                previous_index = state.index
                parsed = rule.parse(self, state, match)
                if parsed is not None:
                    return parsed
                if state.index != previous_index:
                    continue

            return self._parse_paragraph(state)
        return None

    def _assert_streaming_supported(self) -> None:
        if not self._defer_inlines:
            return
        raise StreamingUnsupportedError(
            'streaming output requires rules without deferred inline transforms; use the streaming preset'
        )

    def parse_inlines(self, text: str, state: BlockState | None = None) -> list[Node]:
        if state is not None and state.defer_inlines:
            pending_nodes: list[Node] = []
            state.pending_inlines.append((pending_nodes, text))
            return pending_nodes

        inline_state = state if state is not None else BlockState([])
        nodes: list[Node] = []
        search_cache: InlineSearchCache = {}
        pos = 0

        while pos < len(text):
            found = self._find_inline_match(text, pos, search_cache)

            if found is None:
                nodes.append(Text(value=text[pos:]))
                break

            start, rule, match = found
            if start > pos:
                nodes.append(Text(value=text[pos:start]))

            node, end = rule.parse(self, text, match, inline_state)
            if node is None or end <= start:
                nodes.append(Text(value=text[start : start + 1]))
                pos = start + 1
            else:
                nodes.append(node)
                pos = end

        nodes = merge_text(nodes)
        if self._emphasis_enabled and contains_emphasis_marker(nodes):
            nodes = parse_emphasis_sequence(nodes)
        return merge_text(nodes)

    def _find_inline_match(
        self, text: str, pos: int, search_cache: InlineSearchCache
    ) -> tuple[int, InlineRule, re.Match[str]] | None:
        found = self._find_search_inline_match(text, pos, search_cache)
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

    def _find_search_inline_match(
        self, text: str, pos: int, search_cache: InlineSearchCache
    ) -> tuple[int, InlineRule, re.Match[str]] | None:
        cached_text = search_cache.get('text')
        cached_pos = search_cache.get('pos')
        cached_found = search_cache.get('found')
        if cached_text is text and isinstance(cached_pos, int) and cached_pos <= pos:
            if cached_found is None:
                return None
            cached_match = cast(tuple[int, InlineRule, re.Match[str]], cached_found)
            if pos <= cached_match[0]:
                return cached_match

        found: tuple[int, InlineRule, re.Match[str]] | None = None
        for rule in self._search_inline_rules:
            match = rule.compiled.search(text, pos)
            if match is None:
                continue
            candidate = (match.start(), rule, match)
            if found is None or self._inline_candidate_before(candidate, found):
                found = candidate
        search_cache['text'] = text
        search_cache['pos'] = pos
        search_cache['found'] = found
        return found

    def _inline_candidate_before(
        self, candidate: tuple[int, InlineRule, re.Match[str]], current: tuple[int, InlineRule, re.Match[str]]
    ) -> bool:
        if candidate[0] != current[0]:
            return candidate[0] < current[0]
        return self._inline_rule_order[candidate[1].name] < self._inline_rule_order[current[1].name]

    def _parse_paragraph(self, state: BlockState) -> Node:
        lines: list[str] = []
        while not state.done:
            line = state.line
            if line.strip() == '':
                break
            if lines:
                for parse_continuation in self._paragraph_continuations:
                    parsed = parse_continuation(self, state, lines)
                    if parsed is not None:
                        return parsed
            if lines and self.is_paragraph_interrupt(line, state):
                break
            lines.append(line.lstrip(' \t') if lines else line)
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

    @staticmethod
    def _collect_root_transforms(rules: list[Rule]) -> list[RootTransform]:
        transforms: list[RootTransform] = []
        seen: set[str] = set()
        for rule in rules:
            for transform in rule.root_transforms:
                if transform.name in seen:
                    continue
                seen.add(transform.name)
                transforms.append(transform)
        return transforms

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


def contains_emphasis_marker(nodes: list[Node]) -> bool:
    for node in nodes:
        if isinstance(node, Text) and node._parse_emphasis and ('*' in node.value or '_' in node.value):
            return True
    return False


def sorted_by_order(rules: list[T]) -> list[T]:
    return [rule for _, rule in sorted(enumerate(rules), key=lambda item: (item[1].order, item[0]))]
