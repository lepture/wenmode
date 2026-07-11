from __future__ import annotations

from collections.abc import Iterable, Iterator, Mapping
from types import MappingProxyType
from typing import cast

from ._parser.blocks import BlockParser
from ._parser.inlines import InlineParser
from ._parser.ruleset import RuleSet, resolve_rule
from .nodes import Node, Root
from .rules.base import BlockRule, InlineRule, Rule
from .rules.transforms import RootTransform
from .state import (
    BlockState,
    LineSource,
    NullSourceTracker,
    PositionSourceTracker,
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
        self._rules: Mapping[str, Rule] = MappingProxyType(self._ruleset.rules)
        self._block_rules: tuple[BlockRule, ...] = tuple(self._ruleset.block_rules)
        self._inline_rules: tuple[InlineRule, ...] = tuple(self._ruleset.inline_rules)
        self._root_transforms: tuple[RootTransform, ...] = tuple(self._ruleset.root_transforms)
        self._inline_parser = InlineParser(self, self._ruleset)
        self._block_parser = BlockParser(self, self._ruleset)
        self.register_rules(rules)

    @property
    def rules(self) -> Mapping[str, Rule]:
        return self._rules

    @property
    def block_rules(self) -> tuple[BlockRule, ...]:
        return self._block_rules

    @property
    def inline_rules(self) -> tuple[InlineRule, ...]:
        return self._inline_rules

    @property
    def root_transforms(self) -> tuple[RootTransform, ...]:
        return self._root_transforms

    @property
    def supports_streaming(self) -> bool:
        """Return whether this parser can yield nodes incrementally."""
        return not self._ruleset.defer_inlines

    def streaming_blockers(self) -> list[str]:
        """Return deferred transform names that prevent streaming output."""
        return list(self._ruleset.streaming_blockers)

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
        self._rules = MappingProxyType(self._ruleset.rules)
        self._block_rules = tuple(self._ruleset.block_rules)
        self._inline_rules = tuple(self._ruleset.inline_rules)
        self._root_transforms = tuple(self._ruleset.root_transforms)
        self._inline_parser.update_rule_set(self._ruleset)
        self._block_parser.update_rule_set(self._ruleset)

    def parse(self, source: LineSource) -> Root:
        """Parse Markdown into a root node.

        :param source: Markdown source as a string or an iterable of lines.
        :returns: Parsed document root.
        """
        state = self._create_block_state(source, defer_inlines=self._ruleset.defer_inlines)
        root = Root(children=self._block_parser.parse_nodes(state))
        if self.positions:
            root._line_starts = create_line_starts(state.lines)
            root.position = state.source.position_between(0, len(state.lines))
        for transform in self.root_transforms:
            transform.prepare(self, root, state)
        self._inline_parser.resolve_pending(state)
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
            node = self._block_parser.parse_next_node(state)
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
        return self._block_parser.parse_blocks(text, parent_state, source)

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

    def _assert_streaming_supported(self) -> None:
        blockers = self.streaming_blockers()
        if not blockers:
            return
        names = ', '.join(blockers)
        raise StreamingUnsupportedError(
            f'streaming output is blocked by deferred inline transforms: {names}; use the streaming preset'
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

    def is_paragraph_interrupt(self, line: str, state: BlockState | None = None) -> bool:
        """Return whether a line would interrupt a paragraph.

        Custom block parsing code can use this helper to mirror the parser's
        paragraph-interruption behavior.

        :param line: Candidate source line.
        :param state: Current block state, if available.
        :returns: ``True`` if the line starts an interrupting block.
        """
        return self._block_parser.is_paragraph_interrupt(line, state)

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
