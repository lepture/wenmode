from __future__ import annotations

import re
from collections.abc import Callable
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Node, Paragraph

from . import interrupts
from .ruleset import RuleSet
from .source import NullSourceTracker, PositionSourceTracker, SourceCollector, SourceMap
from .state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser
    from wenmode.rules import BlockRule, ContinueRule, NodeTransform


class BlockParser:
    """Parse block Markdown with a compiled rule set."""

    def __init__(self, parser: Parser, rule_set: RuleSet) -> None:
        self._parser = parser
        self._rule_set = rule_set

    def update_rule_set(self, rule_set: RuleSet) -> None:
        self._rule_set = rule_set

    def parse_blocks(self, text: str, parent_state: BlockState, source: SourceMap | None = None) -> list[Node]:
        lines = text.splitlines(keepends=True)
        state = self._create_nested_state(lines, parent_state, source)
        if parent_state.depth >= self._parser.max_container_depth - 1:
            return self._parse_shallow_blocks(state)
        return self.parse_nodes(state)

    def _create_nested_state(
        self, lines: list[str], parent_state: BlockState, source: SourceMap | None = None
    ) -> BlockState:
        source_tracker: NullSourceTracker
        if self._parser.positions and source is not None:
            source_tracker = PositionSourceTracker(source.line_offsets(lines))
        else:
            source_tracker = NullSourceTracker()
        pending_inlines, pending_callbacks, inline_sources = parent_state.deferred_state()
        return BlockState(
            lines,
            source=source_tracker,
            store=parent_state.store,
            depth=parent_state.depth + 1,
            defer_inlines=parent_state.defer_inlines,
            _pending_inlines=pending_inlines,
            _pending_inline_callbacks=pending_callbacks,
            _inline_sources=inline_sources,
        )

    def _parse_shallow_blocks(self, state: BlockState) -> list[Node]:
        children: list[Node] = []

        while not state.done:
            while not state.done and state.line.strip() == '':
                state.advance()
            if state.done:
                break

            start_index = state.index
            node = self._parse_shallow_paragraph(state)
            children.append(self._with_position(node, state, start_index) if self._parser.positions else node)

        return children

    def _parse_shallow_paragraph(self, state: BlockState) -> Node:
        if self._parser.positions:
            return self._parse_positioned_shallow_paragraph(state)
        return self._parse_plain_shallow_paragraph(state)

    def _parse_plain_shallow_paragraph(self, state: BlockState) -> Node:
        lines = self._read_shallow_paragraph_lines(state)
        return self._paragraph_from_lines(state, lines)

    def _parse_positioned_shallow_paragraph(self, state: BlockState) -> Node:
        source = state.source.collect()
        lines = self._read_shallow_paragraph_lines(state, source)
        return self._paragraph_from_lines(state, lines, source)

    @staticmethod
    def _read_shallow_paragraph_lines(state: BlockState, source: SourceCollector | None = None) -> list[str]:
        lines: list[str] = []
        while not state.done and state.line.strip() != '':
            _append_paragraph_line(state, source, lines, state.line)
        return lines

    def parse_nodes(self, state: BlockState) -> list[Node]:
        children: list[Node] = []

        while not state.done:
            node = self.parse_next_node(state)
            if node is not None:
                children.append(node)

        return children

    def parse_next_node(self, state: BlockState) -> Node | None:
        while True:
            while not state.done and state.line.strip() == '':
                state.advance()
            if state.done:
                return None

            start_index = state.index
            line = state.line
            if interrupts.is_plain_paragraph_start(self._rule_set, line):
                parsed = self._parse_paragraph(state)
                return self._with_position(parsed, state, start_index) if self._parser.positions else parsed

            parsed_block, consumed = self._try_parse_block(state, line)
            if parsed_block is not None:
                return self._with_position(parsed_block, state, start_index) if self._parser.positions else parsed_block
            if consumed:
                continue

            parsed = self._parse_paragraph(state)
            return self._with_position(parsed, state, start_index) if self._parser.positions else parsed

    def is_paragraph_interrupt(self, line: str, state: BlockState | None = None) -> bool:
        return interrupts.is_paragraph_interrupt(self._rule_set, self._parser.max_container_depth, line, state)

    def container_depth_exceeded(self, name: str, state: BlockState | None) -> bool:
        return interrupts.container_depth_exceeded(name, state, self._parser.max_container_depth)

    @staticmethod
    def _with_position(node: Node, state: BlockState, start_index: int) -> Node:
        if node.position is None:
            node.position = state.source.position_between(start_index, state.index)
        return node

    def _try_parse_block(self, state: BlockState, line: str) -> tuple[Node | None, bool]:
        match = self._block_opener_match(line, state)
        if match is None:
            return None, False
        return self._parse_matching_block_rule(state, match)

    def _block_opener_match(self, line: str, state: BlockState) -> re.Match[str] | None:
        if self._rule_set.block_openers is None:
            return None
        match = self._rule_set.block_openers.match(line)
        if match is None:
            return None
        if self.container_depth_exceeded(cast(str, match.lastgroup), state):
            return None
        return match

    def _parse_matching_block_rule(self, state: BlockState, match: re.Match[str]) -> tuple[Node | None, bool]:
        line = state.line
        first_rule_name = cast(str, match.lastgroup)
        start = self._rule_set.block_rule_order[first_rule_name]
        for rule in self._rule_set.block_rules[start:]:
            candidate = rule.match_candidate(line)
            if candidate is None or self.container_depth_exceeded(rule.name, state):
                continue
            previous_index = state.index
            parsed = rule.parse(self._parser, state, candidate)
            if state.index < previous_index:
                raise RuntimeError(
                    f"Block rule '{rule.name}' moved state backwards from index {previous_index} to {state.index}"
                )
            if parsed is not None:
                if state.index == previous_index:
                    raise RuntimeError(f"Block rule '{rule.name}' returned a node but state did not advance")
                parsed = apply_node_transforms(rule, self._parser, parsed, state)
                return parsed, True
            if state.index > previous_index:
                return None, True
        return None, False

    def _parse_paragraph(self, state: BlockState) -> Node:
        if self._parser.positions:
            return self._parse_positioned_paragraph(state)
        return self._parse_plain_paragraph(state)

    def _parse_plain_paragraph(self, state: BlockState) -> Node:
        lines, parsed = self._read_paragraph_lines(state)
        if parsed is not None:
            return parsed
        return self._paragraph_from_lines(state, lines)

    def _parse_positioned_paragraph(self, state: BlockState) -> Node:
        source = state.source.collect()
        lines, parsed = self._read_paragraph_lines(state, source)
        if parsed is not None:
            return parsed
        return self._paragraph_from_lines(state, lines, source)

    def _paragraph_from_lines(
        self, state: BlockState, lines: list[str], source: SourceCollector | None = None
    ) -> Paragraph:
        if source is None:
            text = ''.join(lines).strip()
            return Paragraph(children=self._parser.parse_inlines(text, state))

        inline_source = source.map()
        if inline_source is None:
            text = ''.join(lines).strip()
            return Paragraph(children=self._parser.parse_inlines(text, state))

        raw_text = inline_source.text
        start = len(raw_text) - len(raw_text.lstrip())
        end = len(raw_text.rstrip())
        inline_source = inline_source.slice(start, end)
        text = inline_source.text
        return Paragraph(children=self._parser.parse_inlines(text, state, source=inline_source))

    def _read_paragraph_lines(
        self, state: BlockState, source: SourceCollector | None = None
    ) -> tuple[list[str], Node | None]:
        lines: list[str] = []
        while not state.done:
            line = state.line
            if line.strip() == '':
                break
            if lines:
                parsed = self._parse_paragraph_continuation(state, lines, line)
                if parsed is not None:
                    return lines, parsed
            if lines and self.is_paragraph_interrupt(line, state):
                break
            _append_paragraph_line(state, source, lines, line)
        return lines, None

    def _parse_paragraph_continuation(self, state: BlockState, lines: list[str], line: str) -> Node | None:
        for continuation in self._rule_set.paragraph_continuations:
            candidate = continuation.match_candidate(line)
            if candidate is None:
                continue
            previous_index = state.index
            parsed = continuation.parse_paragraph_continuation(self._parser, state, lines, candidate)
            if parsed is None:
                if state.index != previous_index:
                    raise RuntimeError(
                        f"Continuation rule '{continuation.name}' returned None but declining continuation "
                        f'changed state from index {previous_index} to {state.index}'
                    )
                return None
            if state.index < previous_index:
                raise RuntimeError(
                    f"Continuation rule '{continuation.name}' moved state backwards "
                    f'from index {previous_index} to {state.index}'
                )
            if state.index == previous_index:
                raise RuntimeError(f"Continuation rule '{continuation.name}' returned a node but state did not advance")
            parsed = apply_node_transforms(continuation, self._parser, parsed, state)
            return parsed
        return None


def _append_paragraph_line(state: BlockState, source: SourceCollector | None, lines: list[str], line: str) -> None:
    if lines:
        text = line.lstrip(' \t')
    else:
        text = line
    if source is not None:
        source.add(state.index, len(line) - len(text), text)
    lines.append(text)
    state.advance()


def apply_node_transforms(rule: BlockRule | ContinueRule, parser: Parser, node: Node, state: BlockState) -> Node:
    for transform in rule.node_transforms:
        if state.defer_inlines and transform.defer_inlines:
            state.defer_inline_callback(_deferred_node_transform(transform, parser, node, state))
            continue
        transform.transform(parser, node, state)
    return node


def _deferred_node_transform(
    transform: NodeTransform, parser: Parser, node: Node, state: BlockState
) -> Callable[[], None]:
    def run_transform() -> None:
        transform.transform(parser, node, state)

    return run_transform
