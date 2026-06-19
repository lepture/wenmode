from __future__ import annotations

import re
import string
from collections.abc import Callable, Iterable, Iterator
from typing import TypeVar, cast

from .nodes import Node, Paragraph, Point, Root, Text
from .rules.base import BlockRule, ContinueRule, InlineRule, Rule
from .rules.blocks.html import is_html_block_tag
from .rules.inlines.emphasis import parse_emphasis_sequence
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

LIST_MARKER_RE = re.compile(
    r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?P<spaces>[ \t]+|$)(?P<rest>.*)$'
)
HTML_TAG_START_RE = re.compile(r'</?[A-Za-z]')
HTML_PARAGRAPH_INTERRUPT_RE = re.compile(r'(?i)<(?:script|pre|style|textarea)(?:\s|>|$)')
PUNCTUATION = set(string.punctuation)
T = TypeVar('T', bound=Rule)
InlineSearchCache = dict[str, object]


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
        self._inline_sources: list[SourceMap] = []
        self.register_rules(rules)

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
        resolved_rules = list(self._registered_rules)
        root_transforms = collect_root_transforms(resolved_rules)
        for transform in root_transforms:
            for required in transform.required_rules:
                rule = resolve_rule(required)
                if all(registered.name != rule.name for registered in resolved_rules):
                    resolved_rules.append(rule)

        self.rules = {rule.name: rule for rule in resolved_rules}
        self.block_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, BlockRule)])
        self.inline_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, InlineRule)])
        self.root_transforms = root_transforms
        self._paragraph_continuations = [rule for rule in resolved_rules if isinstance(rule, ContinueRule)]
        self._emphasis_enabled = 'emphasis' in self.rules
        self._defer_inlines = any(transform.defer_inlines for transform in root_transforms)
        self._inline_rule_order = {rule.name: index for index, rule in enumerate(self.inline_rules)}
        self._triggered_inline_rules, self._search_inline_rules = prepare_inline_dispatch(self.inline_rules)
        self._inline_trigger_re = compile_inline_trigger_re(self._triggered_inline_rules)
        self._block_openers = compile_block_openers(self.block_rules)

    def parse(self, source: LineSource) -> Root:
        """Parse Markdown into a root node.

        :param source: Markdown source as a string or an iterable of lines.
        :returns: Parsed document root.
        """
        state = self._create_block_state(source, defer_inlines=self._defer_inlines)
        root = Root(children=self._parse_block_nodes(state))
        if self.positions:
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
        need deferred inline resolution.

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
            source_tracker = PositionSourceTracker(source.line_points(lines))
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
        )
        return self._parse_block_nodes(state)

    def _create_block_state(self, source: LineSource, defer_inlines: bool) -> BlockState:
        source_tracker: NullSourceTracker
        if isinstance(source, str):
            lines = source.splitlines(keepends=True)
            if self.positions:
                source_tracker = PositionSourceTracker(create_line_points(lines))
            else:
                source_tracker = NullSourceTracker()
            return BlockState(
                lines,
                source=source_tracker,
                defer_inlines=defer_inlines,
            )

        line_buffer = StreamLineBuffer(source, track_positions=self.positions)
        if self.positions:
            source_tracker = PositionSourceTracker(cast(list[Point], line_buffer.line_points))
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

            if self._block_openers:
                match = self._block_openers.match(line)
            else:
                match = None
            if match is not None and not self._container_depth_exceeded(match, state):
                rule = self._match_block_rule(match)
                previous_index = state.index
                parsed_block = rule.parse(self, state, match)
                if parsed_block is not None:
                    if self.positions and parsed_block.position is None:
                        parsed_block.position = state.source.position_between(start_index, state.index)
                    return parsed_block
                if state.index != previous_index:
                    continue

            parsed = self._parse_paragraph(state)
            if self.positions and parsed.position is None:
                parsed.position = state.source.position_between(start_index, state.index)
            return parsed
        return None

    def _assert_streaming_supported(self) -> None:
        if not self._defer_inlines:
            return
        raise StreamingUnsupportedError(
            'streaming output requires rules without deferred inline transforms; use the streaming preset'
        )

    def parse_inlines(self, text: str, state: BlockState | None = None, source: SourceMap | None = None) -> list[Node]:
        """Parse inline Markdown into child nodes.

        Custom inline, block, and continuation rules can call this method when
        they need nested inline parsing.

        :param text: Inline Markdown source.
        :param state: Current block state, if parsing happens inside a document
            parse.
        :param source: Optional source map for ``text`` when positions are
            enabled.
        :returns: Parsed inline nodes.
        """
        if state is not None and state.defer_inlines:
            return self._defer_inline_parse(text, state, source)

        if state is None:
            state = BlockState([])

        if not self.positions:
            return self._parse_inline_nodes(text, state)
        return self._parse_inline_nodes_with_positions(text, state, source)

    def _defer_inline_parse(self, text: str, state: BlockState, source: SourceMap | None) -> list[Node]:
        pending_nodes: list[Node] = []
        if self.positions:
            pending_source = source
        else:
            pending_source = None
        state.pending_inlines.append((pending_nodes, text, pending_source))
        return pending_nodes

    def _parse_inline_nodes(self, text: str, state: BlockState) -> list[Node]:
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

            node, end = rule.parse(self, text, match, state)
            if node is None or end <= start:
                nodes.append(Text(value=text[start : start + 1]))
                pos = start + 1
            else:
                nodes.append(node)
                pos = end

        return self._finalize_inline_nodes(nodes)

    def _parse_inline_nodes_with_positions(self, text: str, state: BlockState, source: SourceMap | None) -> list[Node]:
        nodes: list[Node] = []
        search_cache: InlineSearchCache = {}
        pos = 0

        if source is not None:
            self._inline_sources.append(source)
        try:
            while pos < len(text):
                found = self._find_inline_match(text, pos, search_cache)

                if found is None:
                    nodes.append(self._text_node(text, pos, len(text), source))
                    break

                start, rule, match = found
                if start > pos:
                    nodes.append(self._text_node(text, pos, start, source))

                node, end = rule.parse(self, text, match, state)
                if node is None or end <= start:
                    nodes.append(self._text_node(text, start, start + 1, source))
                    pos = start + 1
                else:
                    if source is not None and node.position is None:
                        node.position = source.position(start, end)
                    nodes.append(node)
                    pos = end
            return self._finalize_inline_nodes(nodes)
        finally:
            if source is not None:
                self._inline_sources.pop()

    def _finalize_inline_nodes(self, nodes: list[Node]) -> list[Node]:
        nodes = merge_text(nodes)
        if self._emphasis_enabled and contains_emphasis_marker(nodes):
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
        for rule in self._search_inline_rules:
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
        return self._inline_rule_order[candidate[1].name] < self._inline_rule_order[current[1].name]

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
                for continuation in self._paragraph_continuations:
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
        state.defer_inlines = False
        pending = list(state.pending_inlines)
        state.pending_inlines.clear()
        for nodes, text, source in pending:
            nodes[:] = self.parse_inlines(text, state, source=source)
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
        """Return whether a line would interrupt a paragraph.

        Custom block parsing code can use this helper to mirror the parser's
        paragraph-interruption behavior.

        :param line: Candidate source line.
        :param state: Current block state, if available.
        :returns: ``True`` if the line starts an interrupting block.
        """
        if self._block_openers is None:
            return False
        match = self._block_openers.match(line)
        if match is None:
            return False
        if self._container_depth_exceeded(match, state):
            return False
        if match.lastgroup in {'reference_definition', 'table'}:
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

    def inline_source(self, text: str, start: int, end: int) -> SourceMap | None:
        """Return a source map for a slice of the active inline source."""
        if not self.positions:
            return None
        for source in reversed(self._inline_sources):
            if source.text == text:
                return source.slice(start, end)
        return None

    def _text_node(self, text: str, start: int, end: int, source: SourceMap | None) -> Text:
        node = Text(value=text[start:end])
        if source is not None:
            node.position = source.position(start, end)
        return node


def merge_text(nodes: list[Node]) -> list[Node]:
    merged: list[Node] = []
    for node in nodes:
        if (
            isinstance(node, Text)
            and merged
            and isinstance(merged[-1], Text)
            and node._parse_emphasis == merged[-1]._parse_emphasis
        ):
            if merged[-1].position is not None and node.position is not None:
                merged[-1].position = type(merged[-1].position)(start=merged[-1].position.start, end=node.position.end)
            merged[-1].value += node.value
        else:
            merged.append(node)
    return merged


def contains_emphasis_marker(nodes: list[Node]) -> bool:
    for node in nodes:
        if isinstance(node, Text) and node._parse_emphasis and ('*' in node.value or '_' in node.value):
            return True
    return False


def resolve_rule(rule: type[Rule] | Rule) -> Rule:
    if isinstance(rule, type):
        return cast(Callable[[], Rule], rule)()
    return rule


def sorted_by_order(rules: list[T]) -> list[T]:
    return [rule for _, rule in sorted(enumerate(rules), key=lambda item: (item[1].order, item[0]))]


def create_line_points(lines: list[str]) -> list[Point]:
    points: list[Point] = []
    point = Point(line=1, column=1, offset=0)
    for line in lines:
        points.append(point)
        length = len(line)
        offset = point.offset + length
        if length > 0 and line[length - 1] == '\n':
            point = Point(line=point.line + 1, column=1, offset=offset)
        else:
            point = Point(line=point.line, column=point.column + length, offset=offset)
    return points


def collect_root_transforms(rules: list[Rule]) -> list[RootTransform]:
    transforms: list[RootTransform] = []
    seen: set[str] = set()
    for rule in rules:
        for transform in rule.root_transforms:
            if transform.name in seen:
                continue
            seen.add(transform.name)
            transforms.append(transform)
    return transforms


def compile_block_openers(rules: list[BlockRule]) -> re.Pattern[str] | None:
    patterns = [f'(?P<{rule.name}>{rule.pattern})' for rule in rules]
    if patterns:
        return re.compile('|'.join(patterns))
    return None


def prepare_inline_dispatch(rules: list[InlineRule]) -> tuple[dict[str, list[InlineRule]], list[InlineRule]]:
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


def compile_inline_trigger_re(rules: dict[str, list[InlineRule]]) -> re.Pattern[str] | None:
    if not rules:
        return None
    return re.compile(f'[{re.escape("".join(rules))}]')
