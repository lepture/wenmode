from __future__ import annotations

import re
import string

from wenmode.rules.blocks.table import Table, is_delimiter_row, starts_table
from wenmode.utils import count_indent_from, is_html_block_tag

from .ruleset import RuleSet
from .state import BlockState

ListMarker = tuple[str | None, str]

LIST_MARKER_RE = re.compile(r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?:[ \t]+|$)')
HTML_TAG_START_RE = re.compile(r'</?[A-Za-z]')
HTML_PARAGRAPH_INTERRUPT_RE = re.compile(r'<(?:script|pre|style|textarea)(?:\s|>|$)', re.I)
PUNCTUATION = set(string.punctuation)
SETEXT_DASHES_RE = re.compile(r' {0,3}-+[ \t]*$')


def is_paragraph_interrupt(
    rule_set: RuleSet, max_container_depth: int, line: str, state: BlockState | None = None
) -> bool:
    """Return whether a line starts a block that can interrupt a paragraph."""
    if rule_set.block_openers_re is None:
        return False
    match = rule_set.block_openers_re.match(line)
    if match is None:
        return False

    rule_name = match.lastgroup
    if rule_name is None:
        return False

    start = rule_set.block_rule_order[rule_name]
    for rule in rule_set.block_rules[start:]:
        if rule.match_candidate(line) is None or container_depth_exceeded(rule.name, state, max_container_depth):
            continue
        if block_opener_interrupts_paragraph(rule.name, line):
            return True
    return False


def block_opener_interrupts_paragraph(rule_name: str, line: str) -> bool:
    if rule_name in {'reference_definition', 'table'}:
        return False
    if rule_name == 'list':
        return list_interrupts_paragraph(line)
    if rule_name == 'html_block':
        return html_block_interrupts_paragraph(line)
    return rule_name != 'indented_code'


def list_interrupts_paragraph(line: str) -> bool:
    marker = parse_list_marker(line.rstrip('\r\n'))
    if marker is None:
        return True

    ordered, rest = marker
    if rest.strip() == '':
        return False
    if ordered is not None and ordered != '1':
        return False
    return True


def parse_list_marker(line: str) -> ListMarker | None:
    marker = LIST_MARKER_RE.match(line)
    if marker is None:
        return None
    return marker.group('ordered'), line[marker.end() :]


def html_block_interrupts_paragraph(line: str) -> bool:
    stripped = line.lstrip(' \t')
    if is_html_block_tag(stripped):
        return True
    if HTML_TAG_START_RE.match(stripped) and not HTML_PARAGRAPH_INTERRUPT_RE.match(stripped):
        return False
    return True


def has_table_rule(rule_set: RuleSet) -> bool:
    return isinstance(rule_set.rules.get('table'), Table)


def table_interrupts_paragraph(rule_set: RuleSet, state: BlockState) -> bool:
    """Return whether a GFM table header row and its delimiter row end the paragraph.

    Only paragraph parsing asks this, once it knows a table rule is configured: a
    lazy continuation line or a table body row never starts a table.
    """
    if not starts_table(state):
        return False
    # A setext underline takes precedence over a delimiter row without pipes.
    return 'setext_heading' not in rule_set.rules or SETEXT_DASHES_RE.match(state.peek(1).rstrip('\r\n')) is None


def is_table_delimiter_attempt(line: str) -> bool:
    """Return whether a paragraph line is a delimiter row tried against the line above as a table header."""
    return count_indent_from(line) < 4 and is_delimiter_row(line)


def container_depth_exceeded(name: str, state: BlockState | None, max_container_depth: int) -> bool:
    if name not in {'blockquote', 'list'} or state is None:
        return False
    return state.content_depth >= max_container_depth


def is_plain_paragraph_start(rule_set: RuleSet, line: str) -> bool:
    if 'table' in rule_set.rules and '|' in line:
        return False
    char = line[0]
    return not char.isspace() and not char.isdigit() and char not in PUNCTUATION
