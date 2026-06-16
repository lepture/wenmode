from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

from .nodes import Heading, Node, Paragraph, Root, Text
from .rules.base import BlockRule, InlineRule, Rule
from .rules.inlines.emphasis import parse_emphasis_sequence
from .state import BlockState, Reference
from .utils import normalize_label, normalize_label_text, normalize_uri_text


class Wenmode:
    max_container_depth = 100

    def __init__(self, rules: Iterable[type[Any] | Rule]) -> None:
        self.rules = [rule() if isinstance(rule, type) else rule for rule in rules]
        self.block_rules = [rule for rule in self.rules if isinstance(rule, BlockRule)]
        self.inline_rules = [rule for rule in self.rules if isinstance(rule, InlineRule)]
        self._rule_names = {rule.name for rule in self.rules}
        self._setext_heading_enabled = 'setext_heading' in self._rule_names
        self._references_enabled = bool(self._rule_names & {'link', 'image'})
        self._block_openers = self._compile_block_openers(self.block_rules)

    def parse(self, text: str) -> Root:
        return Root(children=self.parse_blocks(text))

    def parse_blocks(self, text: str, parent_state: BlockState | None = None) -> list[Node]:
        references = parent_state.references if parent_state is not None else {}
        if self._references_enabled:
            text, extracted = extract_references(text, self)
            for label, reference in extracted.items():
                references.setdefault(label, reference)
        state = BlockState.from_text(text, references=references, depth=(parent_state.depth + 1 if parent_state else 0))
        children: list[Node] = []

        while not state.done:
            if state.line.strip() == '':
                state.advance()
                continue

            match = self._block_openers.match(state.line) if self._block_openers else None
            if match is not None and not self._container_depth_exceeded(match, state):
                rule = self._match_block_rule(match)
                parsed = rule.parse(self, state, match)
                if parsed is not None:
                    children.append(parsed)
                continue

            children.append(self._parse_paragraph(state))

        return children

    def parse_inlines(self, text: str, state: BlockState | None = None) -> list[Node]:
        nodes: list[Node] = []
        pos = 0
        emphasis_enabled = any(rule.name == 'emphasis' for rule in self.inline_rules)
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

    def is_block_start(self, line: str) -> bool:
        return self._block_openers.match(line) is not None if self._block_openers else False

    def get_reference(self, label: str, state: BlockState | None) -> Reference | None:
        return state.references.get(label) if state is not None else None

    def starts_nonparagraph_block(self, line: str) -> bool:
        return bool(
            ('atx_heading' in self._rule_names and re.match(r'[ \t]{0,3}#{1,6}(?:[ \t]+|$)', line))
            or ('fenced_code' in self._rule_names and re.match(r'[ \t]{0,3}(?:`{3,}|~{3,})', line))
            or ('list' in self._rule_names and re.match(r'[ \t]{0,3}(?:[*+-]|\d{1,9}[.)])(?:[ \t]+|$)', line))
            or ('indented_code' in self._rule_names and re.match(r'[ \t]{4,}', line))
            or ('thematic_break' in self._rule_names and is_thematic_break(line))
        )

    def can_interrupt_after(self, line: str) -> bool:
        stripped = line.lstrip(' \t')
        return bool(
            ('atx_heading' in self._rule_names and re.match(r'#{1,6}(?:[ \t]+|$)', stripped))
            or ('fenced_code' in self._rule_names and re.match(r'(?:`{3,}|~{3,})', stripped))
            or ('blockquote' in self._rule_names and re.match(r'>', stripped))
            or ('list' in self._rule_names and re.match(r'(?:[*+-]|\d{1,9}[.)])(?:[ \t]+|$)', stripped))
        )

    def _parse_paragraph(self, state: BlockState) -> Node:
        lines: list[str] = []
        while not state.done and state.line.strip() != '':
            if self._setext_heading_enabled and lines:
                marker = re.match(r'[ \t]{0,3}(=+|-+)[ \t]*$', state.line)
                if marker is not None:
                    state.advance()
                    depth = 1 if marker.group(1).startswith('=') else 2
                    text = ''.join(lines).strip()
                    return Heading(depth=depth, children=self.parse_inlines(text, state))
            if lines and self.is_paragraph_interrupt(state.line, state):
                break
            lines.append(state.line.lstrip(' \t') if lines else state.line)
            state.advance()

        text = ''.join(lines).strip()
        return Paragraph(children=self.parse_inlines(text, state))

    def _match_block_rule(self, match: re.Match[str]) -> BlockRule:
        group = match.lastgroup
        if group is None:
            raise RuntimeError('block opener matched without a named group')
        for rule in self.block_rules:
            if rule.name == group:
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
        if match.lastgroup == 'list':
            marker = re.match(
                r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?P<spaces>[ \t]+|$)(?P<rest>.*)$',
                line.rstrip('\r\n'),
            )
            if marker is not None and marker.group('rest').strip() == '':
                return False
            if marker is not None and marker.group('ordered') is not None and marker.group('ordered') != '1':
                return False
        if match.lastgroup == 'html_block':
            stripped = line.lstrip(' \t')
            if is_block_html_start(stripped):
                return True
            if re.match(r'</?[A-Za-z]', stripped) and not re.match(
                r'(?i)<(?:script|pre|style|textarea)(?:\s|>|$)', stripped
            ):
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


def is_block_html_start(line: str) -> bool:
    return re.match(
        r'(?i)</?(?:address|article|aside|base|basefont|blockquote|body|caption|center|col|colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|footer|form|frame|frameset|h1|h2|h3|h4|h5|h6|head|header|hr|html|iframe|legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul)(?:\s|/?>|$)',
        line,
    ) is not None


REFERENCE_START_RE = re.compile(r'^[ \t]{0,3}\[(?P<label>(?:\\.|[^\[\]\\\n]){1,999})\]:[ \t]*(?P<rest>.*)$')
FENCE_RE = re.compile(r'^[ \t]{0,3}(`{3,}|~{3,})')


def extract_references(text: str, parser: Wenmode) -> tuple[str, dict[str, Reference]]:
    lines = text.splitlines(keepends=True)
    references: dict[str, Reference] = {}
    output: list[str] = []
    index = 0

    while index < len(lines):
        fence = FENCE_RE.match(lines[index]) if 'fenced_code' in parser._rule_names else None
        if fence is not None:
            fence_char = fence.group(1)[0]
            fence_size = len(fence.group(1))
            output.append(lines[index])
            index += 1
            while index < len(lines):
                output.append(lines[index])
                index += 1
                if re.match(
                    rf'^[ \t]{{0,3}}{re.escape(fence_char)}{{{fence_size},}}[ \t]*$', output[-1].rstrip('\r\n')
                ):
                    break
            continue

        blockquote_reference = parse_blockquote_reference(lines[index]) if 'blockquote' in parser._rule_names else None
        if blockquote_reference is not None:
            label, reference = blockquote_reference
            references.setdefault(label, reference)
            output.append('>\n')
            index += 1
            continue

        multiline_label = parse_multiline_label_reference(lines, index)
        if multiline_label is not None:
            next_index, label, url, title = multiline_label
            references.setdefault(normalize_label(label), Reference(url=url, title=title))
            index = next_index
            continue

        if output and output[-1].strip() and not parser.can_interrupt_after(output[-1]):
            output.append(lines[index])
            index += 1
            continue

        parsed = parse_reference(lines, index)
        if parsed is None:
            output.append(lines[index])
            index += 1
            continue

        next_index, label, url, title = parsed
        references.setdefault(normalize_label(label), Reference(url=url, title=title))
        index = next_index

    return ''.join(output), references


def parse_reference(lines: list[str], index: int) -> tuple[int, str, str, str | None] | None:
    match = REFERENCE_START_RE.match(lines[index].rstrip('\r\n'))
    if match is None:
        return None

    label = normalize_label_text(match.group('label'))
    rest = match.group('rest')
    index += 1

    while rest == '' and index < len(lines):
        continuation = lines[index].rstrip('\r\n')
        if continuation.strip() == '':
            return None
        rest = continuation.strip()
        index += 1

    destination, rest_after_destination = parse_reference_destination(rest)
    if destination is None:
        return None

    title: str | None = None
    if rest_after_destination and not rest_after_destination[0].isspace():
        return None
    remainder = rest_after_destination.strip()
    if remainder:
        parsed_title = parse_reference_title(remainder)
        if parsed_title is None and remainder[0] in '"\'(':
            parsed_title, index = parse_multiline_reference_title(remainder, lines, index)
        if parsed_title is None:
            return None
        title, remainder = parsed_title
        if remainder.strip():
            return None
    elif index < len(lines):
        next_line = lines[index].rstrip('\r\n')
        parsed_title = parse_reference_title(next_line.strip())
        if parsed_title is not None and not parsed_title[1].strip():
            title = parsed_title[0]
            index += 1

    return index, label, normalize_uri_text(destination), title


def parse_reference_destination(text: str) -> tuple[str | None, str]:
    text = text.lstrip()
    if text.startswith('<'):
        end = text.find('>')
        if end == -1:
            return None, text
        destination = text[1:end]
        if '\n' in destination:
            return None, text
        return destination, text[end + 1 :]

    match = re.match(r'(?:\\.|[^\s()\\]|[(](?:\\.|[^()\s\\])*[)])+', text)
    if match is None:
        return None, text
    return match.group(0), text[match.end() :]


def parse_reference_title(text: str) -> tuple[str, str] | None:
    if not text:
        return None
    opener = text[0]
    closer = {'"': '"', "'": "'", '(': ')'}.get(opener)
    if closer is None:
        return None
    index = 1
    escaped = False
    while index < len(text):
        char = text[index]
        if escaped:
            escaped = False
        elif char == '\\':
            escaped = True
        elif char == closer:
            return normalize_label_text(text[1:index]), text[index + 1 :]
        index += 1
    return None


def parse_multiline_reference_title(
    first_line: str, lines: list[str], index: int
) -> tuple[tuple[str, str] | None, int]:
    title_lines = [first_line]
    while index < len(lines):
        if lines[index].strip() == '':
            return None, index
        title_lines.append(lines[index].rstrip('\r\n'))
        index += 1
        parsed = parse_reference_title('\n'.join(title_lines))
        if parsed is not None:
            return parsed, index
    return None, index


def is_thematic_break(line: str) -> bool:
    return bool(
        re.match(r'[ \t]{0,3}(?:\*[ \t]*){3,}$', line)
        or re.match(r'[ \t]{0,3}(?:-[ \t]*){3,}$', line)
        or re.match(r'[ \t]{0,3}(?:_[ \t]*){3,}$', line)
    )


def parse_blockquote_reference(line: str) -> tuple[str, Reference] | None:
    match = re.match(r'^[ \t]{0,3}> ?(.*)$', line.rstrip('\r\n'))
    if match is None:
        return None
    parsed = parse_reference([match.group(1) + '\n'], 0)
    if parsed is None:
        return None
    _, label, url, title = parsed
    return normalize_label(label), Reference(url=url, title=title)


def parse_multiline_label_reference(lines: list[str], index: int) -> tuple[int, str, str, str | None] | None:
    if not re.match(r'^[ \t]{0,3}\[[^\]\n]*$', lines[index].rstrip('\r\n')):
        return None
    label_lines = [lines[index].strip()[1:]]
    cursor = index + 1
    while cursor < len(lines):
        line = lines[cursor].rstrip('\r\n')
        end = re.match(r'^(?P<label_end>[^\]]*)\]:[ \t]*(?P<rest>.*)$', line)
        if end is not None:
            label_lines.append(end.group('label_end'))
            label = normalize_label_text('\n'.join(label_lines))
            if normalize_label(label) == '':
                return None
            destination, rest_after_destination = parse_reference_destination(end.group('rest'))
            if destination is None:
                return None
            title: str | None = None
            remainder = rest_after_destination.strip()
            if remainder:
                parsed_title = parse_reference_title(remainder)
                if parsed_title is None:
                    return None
                title, remainder = parsed_title
                if remainder.strip():
                    return None
            return cursor + 1, label, normalize_uri_text(destination), title
        if line.strip() == '':
            return None
        label_lines.append(line)
        cursor += 1
    return None
