from __future__ import annotations

from collections.abc import Iterable
from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from wenmode import Wenmode
from wenmode.rules import (
    Abbreviation,
    AtxHeading,
    Autolink,
    BackslashEscape,
    Blockquote,
    BlockSpoiler,
    CharacterReference,
    ContainerDirective,
    DefinitionList,
    Emphasis,
    ExtendedAutolink,
    FencedCode,
    FencedDirective,
    Footnote,
    FootnoteDefinition,
    HardBreak,
    HtmlBlock,
    Image,
    IndentedCode,
    InlineCode,
    InlineMath,
    InlineSpoiler,
    Insert,
    LeafDirective,
    Link,
    List,
    Mark,
    MathBlock,
    RawHtml,
    ReferenceDefinition,
    Role,
    Ruby,
    Rule,
    SetextHeading,
    Strikethrough,
    Subscript,
    Superscript,
    Table,
    TextDirective,
    ThematicBreak,
)

RuleSpec = type[Rule] | Rule

POSITION_RULES: dict[str, RuleSpec] = {
    'abbreviation': Abbreviation,
    'atx_heading': AtxHeading,
    'autolink': Autolink,
    'backslash_escape': BackslashEscape,
    'block_spoiler': BlockSpoiler,
    'blockquote': Blockquote,
    'character_reference': CharacterReference,
    'container_directive': ContainerDirective,
    'definition_list': DefinitionList,
    'emphasis': Emphasis,
    'extended_autolink': ExtendedAutolink,
    'fenced_code': FencedCode,
    'fenced_directive': FencedDirective,
    'footnote': Footnote,
    'footnote_definition': FootnoteDefinition,
    'hard_break': HardBreak,
    'heading_id_transform': AtxHeading(id_transform=True),
    'html_block': HtmlBlock,
    'image': Image,
    'indented_code': IndentedCode,
    'inline_code': InlineCode,
    'inline_math': InlineMath,
    'inline_spoiler': InlineSpoiler,
    'insert': Insert,
    'leaf_directive': LeafDirective,
    'link': Link,
    'list': List,
    'mark': Mark,
    'math_block': MathBlock,
    'raw_html': RawHtml,
    'reference_definition': ReferenceDefinition,
    'role': Role,
    'ruby': Ruby,
    'setext_heading': SetextHeading,
    'strikethrough': Strikethrough,
    'subscript': Subscript,
    'superscript': Superscript,
    'table': Table,
    'task_list': List(task=True),
    'text_directive': TextDirective,
    'thematic_break': ThematicBreak,
}


class PositionExample(TypedDict, total=False):
    name: str
    rules: list[str]
    markdown: str
    source_lines: list[str]
    ast: dict[str, object]


def source_for_example(example: PositionExample) -> str | Iterable[str]:
    if 'source_lines' in example:
        return iter(example['source_lines'])
    return example['markdown']


def rules_for_example(example: PositionExample) -> Iterable[RuleSpec] | None:
    if 'rules' in example:
        return [POSITION_RULES[name] for name in example['rules']]
    return None


def test_all_position_rules_have_examples() -> None:
    examples = load_fixture('positions.json')
    used_rules = {
        rule_name
        for example in examples
        for rule_name in example.get('rules', [])
    }
    assert sorted(set(POSITION_RULES) - used_rules) == []


@pytest.mark.parametrize(
    'example',
    load_fixture('positions.json'),
    ids=lambda example: example['name'],
)
def test_position_examples(example: PositionExample) -> None:
    app = Wenmode(rules_for_example(example), positions=True)
    assert app.parse(source_for_example(example)).to_ast() == example['ast']
