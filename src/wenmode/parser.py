from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from typing import cast

from ._parser import interrupts
from ._parser.inlines import InlineParser
from ._parser.ruleset import RuleSet, resolve_rule
from .nodes import Node, Paragraph, Root
from .rules.base import BlockRule, InlineRule, Rule
from .rules.transforms import RootTransform
from .state import (
    BlockState,
    LineSource,
    NullSourceTracker,
    PositionSourceTracker,
    SourceCollector,
    SourceMap,
    StreamBlockState,
    StreamLineBuffer,
)


class StreamingUnsupportedError(ValueError):
    """Raised when a rule set cannot be used for streaming output."""


class Parser:
    """Parse Markdown into Wenmode nodes with an explicit rule set.

    Parser instances are reusable. Per-document state such as reference
    definitions, footnotes, abbreviation definitions, and deferred inline queues
    is created for each parse.

    :param rules: Rule classes or configured rule instances to enable.
    :param positions: Attach source positions to parsed nodes when ``True``.
    """

    max_container_depth = 20

    def __init__(self, rules: Iterable[type[Rule] | Rule], positions: bool = False) -> None:
        self.positions = positions
        self._registered_rules: list[Rule] = []
        self._ruleset = RuleSet.from_rules([])
        self._inline_parser = InlineParser(self, self._ruleset)
        self.register_rules(rules)

    @property
    def rules(self) -> dict[str, Rule]:
        return self._ruleset.rules

    @property
    def block_rules(self) -> list[BlockRule]:
        return self._ruleset.block_rules

    @property
    def inline_rules(self) -> list[InlineRule]:
        return self._ruleset.inline_rules

    @property
    def root_transforms(self) -> list[RootTransform]:
        return self._ruleset.root_transforms

    def register_rule(self, rule: type[Rule] | Rule) -> None:
        """Register or replace one rule by name.

        :param rule: Rule class or configured rule instance.
        """
        self._register_resolved_rule(resolve_rule(rule))
        self._rebuild_rules()

    def register_rules(self, rules: Iterable[type[Rule] | Rule]) -> None:
        """Register or replace multiple rules by name.

        :param rules: Rule classes or configured rule instances.
        """
        for rule in rules:
            self._register_resolved_rule(resolve_rule(rule))
        self._rebuild_rules()

    def _register_resolved_rule(self, rule: Rule) -> None:
        for index, registered in enumerate(self._registered_rules):
            if registered.name == rule.name:
                self._registered_rules[index] = rule
                return
        self._registered_rules.append(rule)

    def _rebuild_rules(self) -> None:
        self._ruleset = RuleSet.from_rules(self._registered_rules)
        self._inline_parser.update_rule_set(self._ruleset)

    def parse(self, source: LineSource) -> Root:
        """Parse Markdown into a root node.

        :param source: Markdown source as a string or an iterable of lines.
        :returns: Parsed document root.
        """
        state = self._create_block_state(source, defer_inlines=self._ruleset.defer_inlines)
        root = Root(children=self._parse_block_nodes(state))
        if self.positions:
            root._line_starts = create_line_starts(state.lines)
            root.position = state.source.position_between(0, len(state.lines))
        for transform in self.root_transforms:
            transform.prepare(self, root, state)
        self._resolve_pending_inlines(state)
        for transform in self.root_transforms:
            transform.transform(self, root, state)
        return root

    def parse_iter(self, source: LineSource) -> Iterator[Node]:
        """Yield top-level block nodes as they are parsed.

        This API is intended for streaming renderers and rejects rule sets that
        need deferred inline resolution. With ``positions=True``, yielded nodes
        store source offsets, but they do not have root-level line-start context;
        calling ``to_ast()`` on them emits offset-only positions.

        :param source: Markdown source as a string or an iterable of lines.
        :returns: Iterator of parsed block nodes.
        :raises StreamingUnsupportedError: If enabled rules require deferred
            inline transforms.
        """
        self._assert_streaming_supported()
        state = self._create_block_state(source, defer_inlines=False)
        while not state.done:
            node = self._parse_next_block_node(state)
            if node is not None:
                yield node

    def parse_blocks(self, text: str, parent_state: BlockState, source: SourceMap | None = None) -> list[Node]:
        """Parse nested block content using a parent parse state.

        Custom block rules should use this helper for nested Markdown content so
        extension state and deferred inline queues are shared with the enclosing
        parse.

        :param text: Markdown block content.
        :param parent_state: Current block state from the outer parse.
        :param source: Optional source map for ``text`` when positions are
            enabled.
        :returns: Parsed child nodes.
        """
        lines = text.splitlines(keepends=True)
        source_tracker: NullSourceTracker
        if self.positions and source is not None:
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
        return self._parse_block_nodes(state)

    def _create_block_state(self, source: LineSource, defer_inlines: bool) -> BlockState:
        source_tracker: NullSourceTracker
        if isinstance(source, str):
            lines = source.splitlines(keepends=True)
            if self.positions:
                source_tracker = PositionSourceTracker(create_line_starts(lines))
            else:
                source_tracker = NullSourceTracker()
            return BlockState(
                lines,
                source=source_tracker,
                defer_inlines=defer_inlines,
            )

        line_buffer = StreamLineBuffer(source, track_positions=self.positions)
        if self.positions:
            source_tracker = PositionSourceTracker(cast(list[int], line_buffer.line_offsets))
        else:
            source_tracker = NullSourceTracker()
        return StreamBlockState(
            line_buffer,
            source=source_tracker,
            defer_inlines=defer_inlines,
        )

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

            start_index = state.index
            if self._is_plain_paragraph_start(line):
                parsed = self._parse_paragraph(state)
                if self.positions and parsed.position is None:
                    parsed.position = state.source.position_between(start_index, state.index)
                return parsed

            if self._ruleset.block_openers:
                match = self._ruleset.block_openers.match(line)
            else:
                match = None
            if match is not None and not self._container_depth_exceeded(cast(str, match.lastgroup), state):
                parsed_block, consumed = self._parse_matching_block_rule(state, match)
                if parsed_block is not None:
                    if self.positions and parsed_block.position is None:
                        parsed_block.position = state.source.position_between(start_index, state.index)
                    return parsed_block
                if consumed:
                    continue

            parsed = self._parse_paragraph(state)
            if self.positions and parsed.position is None:
                parsed.position = state.source.position_between(start_index, state.index)
            return parsed
        return None

    def _parse_matching_block_rule(self, state: BlockState, match: re.Match[str]) -> tuple[Node | None, bool]:
        line = state.line
        first_rule_name = cast(str, match.lastgroup)
        start = self._ruleset.block_rule_order[first_rule_name]
        for rule in self._ruleset.block_rules[start:]:
            rule_match = re.match(rule.pattern, line)
            if rule_match is None or self._container_depth_exceeded(rule.name, state):
                continue
            previous_index = state.index
            parsed = rule.parse(self, state, rule_match)
            if parsed is not None:
                return parsed, True
            if state.index != previous_index:
                return None, True
        return None, False

    def _assert_streaming_supported(self) -> None:
        if not self._ruleset.defer_inlines:
            return
        raise StreamingUnsupportedError(
            'streaming output requires rules without deferred inline transforms; use the streaming preset'
        )

    def parse_inlines(self, text: str, state: BlockState, source: SourceMap | None = None) -> list[Node]:
        """Parse inline Markdown into child nodes.

        Custom inline, block, and continuation rules can call this method when
        they need nested inline parsing.

        :param text: Inline Markdown source.
        :param state: Current block state used for extension state, deferred
            inline queues, and active inline source maps.
        :param source: Optional source map for ``text`` when positions are
            enabled.
        :returns: Parsed inline nodes.
        """
        return self._inline_parser.parse(text, state, source)

    def _parse_paragraph(self, state: BlockState) -> Node:
        if self.positions:
            return self._parse_positioned_paragraph(state)
        return self._parse_plain_paragraph(state)

    def _parse_plain_paragraph(self, state: BlockState) -> Node:
        lines, parsed = self._read_paragraph_lines(state)
        if parsed is not None:
            return parsed
        text = ''.join(lines).strip()
        return Paragraph(children=self.parse_inlines(text, state))

    def _parse_positioned_paragraph(self, state: BlockState) -> Node:
        source = state.source.collect()
        lines, parsed = self._read_paragraph_lines(state, source)
        if parsed is not None:
            return parsed
        inline_source = source.map()
        if inline_source is None:
            text = ''.join(lines).strip()
            return Paragraph(children=self.parse_inlines(text, state))

        raw_text = inline_source.text
        start = len(raw_text) - len(raw_text.lstrip())
        end = len(raw_text.rstrip())
        inline_source = inline_source.slice(start, end)
        text = inline_source.text
        return Paragraph(children=self.parse_inlines(text, state, source=inline_source))

    def _read_paragraph_lines(
        self, state: BlockState, source: SourceCollector | None = None
    ) -> tuple[list[str], Node | None]:
        lines: list[str] = []
        while not state.done:
            line = state.line
            if line.strip() == '':
                break
            if lines:
                for continuation in self._ruleset.paragraph_continuations:
                    if not continuation.matches(line):
                        continue
                    parsed = continuation.parse_paragraph_continuation(self, state, lines)
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

    def _resolve_pending_inlines(self, state: BlockState) -> None:
        self._inline_parser.resolve_pending(state)

    def is_paragraph_interrupt(self, line: str, state: BlockState | None = None) -> bool:
        """Return whether a line would interrupt a paragraph.

        Custom block parsing code can use this helper to mirror the parser's
        paragraph-interruption behavior.

        :param line: Candidate source line.
        :param state: Current block state, if available.
        :returns: ``True`` if the line starts an interrupting block.
        """
        return interrupts.is_paragraph_interrupt(self._ruleset, self.max_container_depth, line, state)

    def _container_depth_exceeded(self, name: str, state: BlockState | None) -> bool:
        return interrupts.container_depth_exceeded(name, state, self.max_container_depth)

    def _is_plain_paragraph_start(self, line: str) -> bool:
        return interrupts.is_plain_paragraph_start(self._ruleset, line)

    def inline_source(self, text: str, state: BlockState, start: int, end: int) -> SourceMap | None:
        """Return a source map for a slice of the state's active inline source."""
        return self._inline_parser.source_for(text, state, start, end)


def create_line_starts(lines: list[str]) -> list[int]:
    starts = [0]
    offset = 0
    for line in lines:
        length = len(line)
        offset += length
        if length > 0 and line[length - 1] == '\n':
            starts.append(offset)
    return starts
