from __future__ import annotations

import re
import string

from .ruleset import RuleSet
from .state import BlockState

ListMarker = tuple[str | None, str]

LIST_MARKER_RE = re.compile(r'^[ \t]{0,3}(?:(?P<bullet>[*+-])|(?P<ordered>\d{1,9})[.)])(?:[ \t]+|$)')
HTML_TAG_START_RE = re.compile(r'</?[A-Za-z]')
HTML_PARAGRAPH_INTERRUPT_RE = re.compile(r'(?i)<(?:script|pre|style|textarea)(?:\s|>|$)')
PUNCTUATION = set(string.punctuation)


def is_paragraph_interrupt(rule_set: RuleSet, max_container_depth: int, line: str, state: BlockState | None = None) -> bool:
    """Return whether a line starts a block that can interrupt a paragraph."""
    if rule_set.block_openers is None:
        return False
    match = rule_set.block_openers.match(line)
    if match is None:
        return False

    rule_name = match.lastgroup
    if rule_name is None or container_depth_exceeded(rule_name, state, max_container_depth):
        return False
    return block_opener_interrupts_paragraph(rule_name, line)


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
    from wenmode.rules.blocks.html import is_html_block_tag

    stripped = line.lstrip(' \t')
    if is_html_block_tag(stripped):
        return True
    if HTML_TAG_START_RE.match(stripped) and not HTML_PARAGRAPH_INTERRUPT_RE.match(stripped):
        return False
    return True


def container_depth_exceeded(name: str, state: BlockState | None, max_container_depth: int) -> bool:
    if name not in {'blockquote', 'list'} or state is None:
        return False
    return state.depth >= max_container_depth


def is_plain_paragraph_start(rule_set: RuleSet, line: str) -> bool:
    if 'table' in rule_set.rules and '|' in line:
        return False
    char = line[0]
    return not char.isspace() and not char.isdigit() and char not in PUNCTUATION
