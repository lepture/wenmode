from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Node, Text
from wenmode.rules.base import InlineCandidate as RuleCandidate
from wenmode.rules.base import InlineRule

from .ruleset import RuleSet
from .source import SourceMap
from .state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser

InlineSearchCache = dict[str, object]
MatchedInlineRule = tuple[InlineRule, RuleCandidate]
InlineCandidateGroup = tuple[int, Sequence[MatchedInlineRule]]


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
                found = self._find_inline_candidate(text, pos, search_cache)

                if found is None:
                    nodes.append(text_node(text, pos, len(text), source))
                    break

                start, rules = found
                if start > pos:
                    nodes.append(text_node(text, pos, start, source))

                if len(rules) == 1:
                    rule, candidate = rules[0]
                    node, end = rule.parse(self._parser, text, candidate, state)
                else:
                    node, end = self._parse_inline_candidate(text, start, state, rules)
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
        if self._rule_set.emphasis_rule is not None and contains_emphasis_marker(nodes):
            nodes = self._rule_set.emphasis_rule.parse_emphasis_sequence(
                nodes, max_depth=self._parser.max_container_depth
            )
        else:
            return nodes
        return merge_text(nodes)

    def _parse_inline_candidate(
        self, text: str, start: int, state: BlockState, rules: Sequence[MatchedInlineRule]
    ) -> tuple[Node | None, int]:
        for rule, candidate in rules:
            node, end = rule.parse(self._parser, text, candidate, state)
            if node is not None and end > start:
                return node, end
        return None, start

    def _find_inline_candidate(
        self, text: str, pos: int, search_cache: InlineSearchCache
    ) -> InlineCandidateGroup | None:
        found = self._search_inline_candidate(text, pos, search_cache)
        if found is not None:
            limit = found[0]
        else:
            limit = len(text)
        if self._rule_set.inline_opener_re is None:
            return found

        opener_end = min(limit + 1, len(text))
        opener_match = self._rule_set.inline_opener_re.search(text, pos, opener_end)
        while opener_match is not None:
            start = opener_match.start()
            if start > limit:
                break
            opener = text[start]
            opener_rules = self._matching_opener_inline_rules(opener, text, start)
            if not opener_rules:
                opener_match = self._rule_set.inline_opener_re.search(text, start + 1, opener_end)
                continue
            if found is not None and start == found[0]:
                return start, self._merge_inline_rules(opener_rules, found[1])
            return start, opener_rules
        return found

    def _search_inline_candidate(
        self, text: str, pos: int, search_cache: InlineSearchCache
    ) -> InlineCandidateGroup | None:
        cached_text = search_cache.get('text')
        cached_pos = search_cache.get('pos')
        cached_found = search_cache.get('found')
        if cached_text is text and isinstance(cached_pos, int) and cached_pos <= pos:
            if cached_found is None:
                return None
            cached = cast(InlineCandidateGroup, cached_found)
            if pos <= cached[0]:
                return cached

        found_start: int | None = None
        found_rules: list[MatchedInlineRule] = []
        for rule in self._rule_set.search_inline_rules:
            candidate = rule.search_candidate(text, pos)
            if candidate is None:
                continue
            start = candidate.start
            if found_start is None or start < found_start:
                found_start = start
                found_rules = [(rule, candidate)]
            elif start == found_start:
                found_rules.append((rule, candidate))
        if found_start is None:
            found: InlineCandidateGroup | None = None
        else:
            found = (found_start, tuple(found_rules))
        search_cache['text'] = text
        search_cache['pos'] = pos
        search_cache['found'] = found
        return found

    def _merge_inline_rules(
        self, first: Sequence[MatchedInlineRule], second: Sequence[MatchedInlineRule]
    ) -> tuple[MatchedInlineRule, ...]:
        return tuple(
            sorted((*first, *second), key=lambda item: self._rule_set.inline_rule_order[item[0].name])
        )

    def _matching_opener_inline_rules(self, opener: str, text: str, start: int) -> Sequence[MatchedInlineRule]:
        opener_rules = self._rule_set.opener_inline_rules[opener]
        if len(opener_rules) == 1:
            rule = opener_rules[0]
            candidate = rule.match_candidate(text, start)
            if candidate is not None:
                return ((rule, candidate),)
            return ()

        matched: list[MatchedInlineRule] = []
        for rule in opener_rules:
            candidate = rule.match_candidate(text, start)
            if candidate is None:
                continue
            matched.append((rule, candidate))
        return tuple(matched)


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
                    text_node_.position = type(text_node_.position)(
                        start=text_node_.position.start, end=node.position.end
                    )
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
