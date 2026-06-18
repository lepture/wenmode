from __future__ import annotations

import json
from pathlib import Path
from typing import TypedDict

import pytest

from wenmode import HTMLRenderer, MarkdownRenderer, RSTRenderer, Wenmode
from wenmode.directives import Admonition, Details, Figure, TableOfContents
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
    Role,
    Ruby,
    SetextHeading,
    Strikethrough,
    Subscript,
    Superscript,
    Table,
    TextDirective,
    ThematicBreak,
)

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
RENDERER_RULES = {
    'abbreviation': Abbreviation,
    'atx_heading': AtxHeading,
    'autolink': Autolink,
    'backslash_escape': BackslashEscape,
    'blockquote': Blockquote,
    'block_spoiler': BlockSpoiler,
    'character_reference': CharacterReference,
    'container_directive': ContainerDirective,
    'definition_list': DefinitionList,
    'emphasis': Emphasis,
    'extended_autolink': ExtendedAutolink,
    'fenced_code': FencedCode,
    'fenced_directive': FencedDirective,
    'footnote': Footnote,
    'hard_break': HardBreak,
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
DEFAULT_RENDERER_RULES = [
    'abbreviation',
    'table',
    'thematic_break',
    'fenced_directive',
    'container_directive',
    'leaf_directive',
    'fenced_code',
    'indented_code',
    'html_block',
    'task_list',
    'atx_heading',
    'setext_heading',
    'blockquote',
    'block_spoiler',
    'definition_list',
    'footnote',
    'math_block',
    'hard_break',
    'autolink',
    'raw_html',
    'backslash_escape',
    'character_reference',
    'image',
    'link',
    'inline_code',
    'inline_math',
    'inline_spoiler',
    'text_directive',
    'role',
    'strikethrough',
    'emphasis',
    'mark',
    'insert',
    'superscript',
    'subscript',
    'ruby',
    'extended_autolink',
]
HTML_DIRECTIVES = {
    'admonition': Admonition,
    'details': Details,
    'figure': Figure,
    'toc': TableOfContents,
}
DEFAULT_HTML_DIRECTIVES = ['admonition', 'details', 'figure', 'toc']


class RendererExample(TypedDict, total=False):
    name: str
    input: str
    rules: list[str]
    html_options: dict[str, bool]
    html_directives: list[str]
    roundtrip_html: bool
    html: str
    markdown: str
    rst: str


def load_renderer_examples() -> list[RendererExample]:
    return json.loads((FIXTURES_DIR / 'renderer.json').read_text())


def rules_for_example(example: RendererExample):
    rule_names = example.get('rules', DEFAULT_RENDERER_RULES)
    return [RENDERER_RULES[name] for name in rule_names]


def html_directives_for_example(example: RendererExample):
    directive_names = example.get('html_directives', DEFAULT_HTML_DIRECTIVES)
    return [HTML_DIRECTIVES[name]() for name in directive_names]


@pytest.mark.parametrize(
    'example',
    load_renderer_examples(),
    ids=lambda example: example['name'],
)
def test_renderer_examples(example: RendererExample) -> None:
    html_renderer = HTMLRenderer(
        directives=html_directives_for_example(example),
        **example.get('html_options', {}),
    )
    rules = rules_for_example(example)
    root = Wenmode(rules).parse(example['input'])
    html = html_renderer.render(root)
    markdown = MarkdownRenderer().render(root)
    rst = RSTRenderer().render(root)

    if example.get('roundtrip_html'):
        assert Wenmode(rules_for_example(example), renderer=html_renderer).render(markdown) == html

    assert html == example['html']
    assert markdown == example['markdown']
    assert rst == example['rst']
