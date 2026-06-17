from __future__ import annotations

import re

import pytest

from wenmode import Parser
from wenmode.nodes import FootnoteDefinition, Paragraph, Root, Text
from wenmode.rules import Footnote as FootnoteRule
from wenmode.rules import FootnoteDefinition as FootnoteDefinitionRule
from wenmode.rules import Role
from wenmode.rules import TextDirective as TextDirectiveInlineRule
from wenmode.rules import directives as directives_module
from wenmode.rules import footnotes as footnotes_module
from wenmode.rules.directives import (
    find_balanced,
    parse_attributes,
    parse_directive_head,
    parse_shortcuts,
    tokenize_attributes,
)
from wenmode.rules.footnotes import collect_definition_lines, collect_footnote_definitions, has_later_continuation
from wenmode.rules.footnotes import strip_indent as strip_footnote_indent
from wenmode.rules.inlines.directive import parse_role
from wenmode.rules.references import (
    parse_multiline_label_reference,
    parse_multiline_reference_title,
    parse_reference,
    parse_reference_destination,
    parse_reference_title,
)
from wenmode.state import BlockState

from ._edge_helpers import (
    render_html,
)


def test_directive_parsing_helpers_and_invalid_inline_directives(monkeypatch: pytest.MonkeyPatch) -> None:
    assert parse_directive_head('1bad') is None
    assert parse_directive_head('name[unterminated') is None
    assert parse_directive_head('name{unterminated') is None
    assert find_balanced(r'[a\[b]', 0, '[', ']') == 5
    assert find_balanced('[a[b]c]', 0, '[', ']') == 6
    assert parse_attributes("#id .one..two key='a\\'b' empty =bad") == {
        'id': 'id',
        'key': "a'b",
        'empty': '',
        'class': 'one two',
    }
    assert parse_attributes('=bad') == {}
    assert tokenize_attributes('  ') == []
    assert tokenize_attributes('a  b') == ['a', 'b']
    monkeypatch.setattr(directives_module, 'tokenize_attributes', lambda text: ['   '])
    assert directives_module.parse_attributes('ignored') == {}
    attributes: dict[str, str] = {}
    classes: list[str] = []
    parse_shortcuts('#.class', attributes, classes)
    assert attributes == {}
    assert classes == ['class']
    parse_shortcuts('x#id', attributes, classes)
    assert attributes == {}

    parser = Parser([TextDirectiveInlineRule])
    assert render_html(parser, ':1\n') == '<p>:1</p>\n'
    text_directive_match = re.match(r':', ':1')
    assert text_directive_match is not None
    assert TextDirectiveInlineRule().parse(Parser([]), ':1', text_directive_match, BlockState([])) == (None, 0)
    role_match = re.match(r'\{', '{1}')
    assert role_match is not None
    assert Role().parse(Parser([]), '{1}', role_match, BlockState([])) == (None, 0)
    assert parse_role('nope') is None
    assert parse_role('{bad') is None
    assert parse_role('{bad name}`x`') is None
    assert parse_role('{role}x') is None
    assert parse_role('{role}`x') is None


def test_reference_and_footnote_edge_branches(monkeypatch: pytest.MonkeyPatch) -> None:
    assert FootnoteRule().parse(Parser([]), '[^x]', re.match(r'\[\^x]', '[^x]')) == (None, 0)  # type: ignore[arg-type]
    assert render_html(Parser([FootnoteRule]), '[^]: bad\n') == '<p>[^]: bad</p>\n'
    footnote_match = re.match(r'.*', '[^x]: note')
    assert footnote_match is not None
    monkeypatch.setattr(footnotes_module, 'normalize_label', lambda label: '')
    assert FootnoteDefinitionRule().parse(Parser([]), BlockState(['[^x]: note\n']), footnote_match) is None

    state = BlockState(['\n'])
    assert has_later_continuation(state) is False
    state = BlockState(['rest\n'])
    assert collect_definition_lines(state, '') == []
    assert collect_definition_lines(BlockState(['def\n', 'x\n']), '') == []
    assert strip_footnote_indent('\tx\n', 2) == 'x\n'
    assert strip_footnote_indent('x\n', 2) == 'x\n'
    first = FootnoteDefinition(identifier='one', children=[])
    duplicate = FootnoteDefinition(identifier='one', children=[Paragraph(children=[Text(value='two')])])
    assert collect_footnote_definitions(Root(children=[first, duplicate])) == {'one': first}
    assert has_later_continuation(BlockState(['def\n', '\n', '  later\n']))

    assert parse_reference(BlockState(['[^x]: /url\n']), 0) is None
    assert parse_reference(BlockState(['[x]:\n', '\n']), 0) is None
    assert parse_reference(BlockState(['[x]: <unterminated\n']), 0) is None
    assert parse_reference(BlockState(['[x]: <line\nbreak>\n']), 0) is None
    assert parse_reference(BlockState(['[x]: <url>title\n']), 0) is None
    assert parse_reference(BlockState(['[x]: /url "unterminated\n']), 0) is None
    assert parse_reference(BlockState(['[x]: /url "title" extra\n']), 0) is None
    assert parse_reference(BlockState(['[x]: /url\n', '"title"\n']), 0) == (2, 'x', '/url', 'title')
    assert parse_reference_destination('<unterminated') == (None, '<unterminated')
    assert parse_reference_destination('<bad\nurl>') == (None, '<bad\nurl>')
    assert parse_reference_destination('') == (None, '')
    assert parse_reference_title('') is None
    assert parse_reference_title('plain') is None
    assert parse_multiline_reference_title('"title', BlockState(['\n']), 0) == (None, 0)
    assert parse_multiline_reference_title('"title', BlockState(['continued"\n']), 0) == (('title\ncontinued', ''), 1)
    assert parse_multiline_label_reference(BlockState(['nope\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[^x\n', ']: /url\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', 'x]: \n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', 'x]: /url "unterminated\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', 'x]: /url "title" extra\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[\n', '\n']), 0) is None
    assert parse_multiline_label_reference(BlockState(['[x\n', ']: /url "title"\n']), 0) == (
        2,
        'x\n',
        '/url',
        'title',
    )
