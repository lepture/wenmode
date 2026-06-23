from __future__ import annotations

import re
from typing import TYPE_CHECKING, cast

from wenmode.nodes import Node, Paragraph
from wenmode.state import (
    BlockState,
    NullSourceTracker,
    PositionSourceTracker,
    SourceCollector,
    SourceMap,
)

from . import interrupts
from .ruleset import RuleSet

if TYPE_CHECKING:
    from wenmode.parser import Parser


class BlockParser:
    """Parse block Markdown with a compiled rule set."""

    def __init__(self, parser: Parser, rule_set: RuleSet) -> None:
        self._parser = parser
        self._rule_set = rule_set

    def update_rule_set(self, rule_set: RuleSet) -> None:
        self._rule_set = rule_set

    def parse_blocks(self, text: str, parent_state: BlockState, source: SourceMap | None = None) -> list[Node]:
        lines = text.splitlines(keepends=True)
        source_tracker: NullSourceTracker
        if self._parser.positions and source is not None:
            source_tracker = PositionSourceTracker(source.line_offsets(lines))
        else:
            source_tracker = NullSourceTracker()
        state = BlockState(
            lines,
            source=source_tracker,
            store=parent_state.store,
            depth=parent_state.depth + 1,
            pending_inlines=parent_state.pending_inlines,
            pending_inline_callbacks=parent_state.pending_inline_callbacks,
            defer_inlines=parent_state.defer_inlines,
            inline_sources=parent_state.inline_sources,
        )
        return self.parse_nodes(state)

    def parse_nodes(self, state: BlockState) -> list[Node]:
        children: list[Node] = []

        while not state.done:
            node = self.parse_next_node(state)
            if node is not None:
                children.append(node)

        return children

    def parse_next_node(self, state: BlockState) -> Node | None:
        while not state.done:
            line = state.line
            if line.strip() == '':
                state.advance()
                continue

            start_index = state.index
            if interrupts.is_plain_paragraph_start(self._rule_set, line):
                parsed = self._parse_paragraph(state)
                if self._parser.positions and parsed.position is None:
                    parsed.position = state.source.position_between(start_index, state.index)
                return parsed

            if self._rule_set.block_openers:
                match = self._rule_set.block_openers.match(line)
            else:
                match = None
            if match is not None and not self.container_depth_exceeded(cast(str, match.lastgroup), state):
                parsed_block, consumed = self._parse_matching_block_rule(state, match)
                if parsed_block is not None:
                    if self._parser.positions and parsed_block.position is None:
                        parsed_block.position = state.source.position_between(start_index, state.index)
                    return parsed_block
                if consumed:
                    continue

            parsed = self._parse_paragraph(state)
            if self._parser.positions and parsed.position is None:
                parsed.position = state.source.position_between(start_index, state.index)
            return parsed
        return None

    def is_paragraph_interrupt(self, line: str, state: BlockState | None = None) -> bool:
        return interrupts.is_paragraph_interrupt(self._rule_set, self._parser.max_container_depth, line, state)

    def container_depth_exceeded(self, name: str, state: BlockState | None) -> bool:
        return interrupts.container_depth_exceeded(name, state, self._parser.max_container_depth)

    def _parse_matching_block_rule(self, state: BlockState, match: re.Match[str]) -> tuple[Node | None, bool]:
        line = state.line
        first_rule_name = cast(str, match.lastgroup)
        start = self._rule_set.block_rule_order[first_rule_name]
        for rule in self._rule_set.block_rules[start:]:
            rule_match = re.match(rule.pattern, line)
            if rule_match is None or self.container_depth_exceeded(rule.name, state):
                continue
            previous_index = state.index
            parsed = rule.parse(self._parser, state, rule_match)
            if parsed is not None:
                return parsed, True
            if state.index != previous_index:
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
        text = ''.join(lines).strip()
        return Paragraph(children=self._parser.parse_inlines(text, state))

    def _parse_positioned_paragraph(self, state: BlockState) -> Node:
        source = state.source.collect()
        lines, parsed = self._read_paragraph_lines(state, source)
        if parsed is not None:
            return parsed
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
                for continuation in self._rule_set.paragraph_continuations:
                    if not continuation.matches(line):
                        continue
                    parsed = continuation.parse_paragraph_continuation(self._parser, state, lines)
                    if parsed is not None:
                        return lines, parsed
            if lines and self.is_paragraph_interrupt(line, state):
                break
            if lines:
                text = line.lstrip(' \t')
            else:
                text = line
            if source is not None:
                source.add(state.index, len(line) - len(text), text)
            lines.append(text)
            state.advance()
        return lines, None
