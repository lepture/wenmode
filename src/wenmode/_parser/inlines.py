from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Node, Text
from wenmode.rules.base import InlineRule
from wenmode.rules.inlines.emphasis import parse_emphasis_sequence
from wenmode.state import BlockState, SourceMap

from .ruleset import RuleSet

if TYPE_CHECKING:
    from wenmode.parser import Parser

InlineSearchCache = dict[str, object]


class InlineParser:
    """Parse inline Markdown with a compiled rule set."""

    def __init__(self, parser: Parser, rule_set: RuleSet) -> None:
        self._parser = parser
        self._rule_set = rule_set

    def update_rule_set(self, rule_set: RuleSet) -> None:
        self._rule_set = rule_set

    def parse(self, text: str, state: BlockState, source: SourceMap | None = None) -> list[Node]:
        if state.defer_inlines:
            return self._defer_inline_parse(text, state, source)

        inline_source = source if self._parser.positions else None
        return self._parse_inline_nodes(text, state, inline_source)

    def resolve_pending(self, state: BlockState) -> None:
        state.defer_inlines = False
        pending = list(state.pending_inlines)
        state.pending_inlines.clear()
        for nodes, text, source in pending:
            nodes[:] = self.parse(text, state, source=source)
        callbacks = list(state.pending_inline_callbacks)
        state.pending_inline_callbacks.clear()
        for callback in callbacks:
            callback()

    def source_for(self, text: str, state: BlockState, start: int, end: int) -> SourceMap | None:
        if not self._parser.positions:
            return None
        for source in reversed(state.inline_sources):
            if source.text == text:
                return source.slice(start, end)
        return None

    def _defer_inline_parse(self, text: str, state: BlockState, source: SourceMap | None) -> list[Node]:
        pending_nodes: list[Node] = []
        if self._parser.positions:
            pending_source = source
        else:
            pending_source = None
        state.pending_inlines.append((pending_nodes, text, pending_source))
        return pending_nodes

    def _parse_inline_nodes(self, text: str, state: BlockState, source: SourceMap | None) -> list[Node]:
        nodes: list[Node] = []
        search_cache: InlineSearchCache = {}
        pos = 0

        if source is not None:
            state.inline_sources.append(source)
        try:
            while pos < len(text):
                found = self._find_inline_match(text, pos, search_cache)

                if found is None:
                    nodes.append(text_node(text, pos, len(text), source))
                    break

                start, rule, match = found
                if start > pos:
                    nodes.append(text_node(text, pos, start, source))

                node, end = rule.parse(self._parser, text, match, state)
                if node is None or end <= start:
                    nodes.append(text_node(text, start, start + 1, source))
                    pos = start + 1
                else:
                    if source is not None and node.position is None:
                        node.position = source.position(start, end)
                    nodes.append(node)
                    pos = end
            return self._finalize_inline_nodes(nodes)
        finally:
            if source is not None:
                state.inline_sources.pop()

    def _finalize_inline_nodes(self, nodes: list[Node]) -> list[Node]:
        nodes = merge_text(nodes)
        if self._rule_set.emphasis_enabled and contains_emphasis_marker(nodes):
            nodes = parse_emphasis_sequence(nodes)
        else:
            return nodes
        return merge_text(nodes)

    def _find_inline_match(
        self, text: str, pos: int, search_cache: InlineSearchCache
    ) -> tuple[int, InlineRule, re.Match[str]] | None:
        found = self._search_inline_match(text, pos, search_cache)
        if found is not None:
            limit = found[0]
        else:
            limit = len(text)
        if self._rule_set.inline_trigger_re is None:
            return found

        trigger_match = self._rule_set.inline_trigger_re.search(text, pos)
        while trigger_match is not None and trigger_match.start() <= limit:
            start = trigger_match.start()
            for rule in self._rule_set.triggered_inline_rules[text[start]]:
                match = rule.compiled.match(text, start)
                if match is None:
                    continue
                candidate = (start, rule, match)
                if found is None or self._inline_candidate_before(candidate, found):
                    return candidate
            trigger_match = self._rule_set.inline_trigger_re.search(text, start + 1)
        return found

    def _search_inline_match(
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
        for rule in self._rule_set.search_inline_rules:
            match = rule.search(text, pos)
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
        return self._rule_set.inline_rule_order[candidate[1].name] < self._rule_set.inline_rule_order[current[1].name]


def text_node(text: str, start: int, end: int, source: SourceMap | None) -> Text:
    node = Text(value=text[start:end])
    if source is not None:
        node.position = source.position(start, end)
    return node


def merge_text(nodes: list[Node]) -> list[Node]:
    merged: list[Node] = []
    text_node_: Text | None = None
    text_parts: list[str] = []

    def flush_text() -> None:
        nonlocal text_node_, text_parts
        if text_node_ is None:
            return
        text_node_.value = ''.join(text_parts)
        merged.append(text_node_)
        text_node_ = None
        text_parts = []

    for node in nodes:
        if isinstance(node, Text):
            if text_node_ is not None and node._parse_emphasis == text_node_._parse_emphasis:
                if text_node_.position is not None and node.position is not None:
                    text_node_.position = type(text_node_.position)(start=text_node_.position.start, end=node.position.end)
                text_parts.append(node.value)
                continue
            flush_text()
            text_node_ = node
            text_parts = [node.value]
            continue

        flush_text()
        merged.append(node)
    flush_text()
    return merged


def contains_emphasis_marker(nodes: list[Node]) -> bool:
    for node in nodes:
        if isinstance(node, Text) and node._parse_emphasis and ('*' in node.value or '_' in node.value):
            return True
    return False
