from __future__ import annotations

import re
from typing import TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import configured_app
from wenmode import HTMLRenderer, MarkdownRenderer, Parser, Wenmode
from wenmode.directives import Figure
from wenmode.nodes import Node, Parent, Text
from wenmode.rules import (
    AtxHeading,
    InlineRule,
    RawHtml,
)
from wenmode.state import BlockState


class RuleEdgeExample(TypedDict, total=False):
    name: str
    rules: list[str]
    markdown: str
    html: str
    max_container_depth: int


class SearchInline(InlineRule):
    order = 10

    def __init__(self) -> None:
        super().__init__('search_inline', r'x')

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        return Text(value='search'), match.end()


class LaterSearchInline(InlineRule):
    order = 20

    def __init__(self) -> None:
        super().__init__('later_search_inline', r'x')

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        return Text(value='later'), match.end()


class TriggerInline(InlineRule):
    order = 30

    def __init__(self) -> None:
        super().__init__('trigger_inline', r'x', 'x')

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        return Text(value='trigger'), match.end()


def app_for_rule_edge(example: RuleEdgeExample) -> Wenmode:
    app = configured_app(example['rules'])
    if 'max_container_depth' in example:
        app.parser.max_container_depth = example['max_container_depth']
    return app


@pytest.mark.parametrize(
    'example',
    load_fixture('rule_edges.json'),
    ids=lambda example: example['name'],
)
def test_rule_edge_examples(example: RuleEdgeExample) -> None:
    assert app_for_rule_edge(example).render(example['markdown']) == example['html']


def test_wenmode_registration_edges() -> None:
    app = Wenmode(rules=[], renderer=HTMLRenderer(), directives=[Figure()])
    assert app.render('# Title\n') == '<p># Title</p>\n'
    app.register_rules([AtxHeading])
    assert app.render('# Title\n') == '<h1>Title</h1>\n'

    with pytest.raises(TypeError):
        Wenmode(renderer=MarkdownRenderer()).register_directive_renderer(Figure())


def test_raw_html_comment_styles() -> None:
    renderer = HTMLRenderer(escape=False, sanitize_urls=False)
    commonmark = Wenmode([RawHtml], renderer=renderer)
    gfm = Wenmode([RawHtml(comment_style='gfm')], renderer=renderer)

    assert (
        commonmark.render('foo <!-- this is a --\ncomment - with hyphens -->\n')
        == '<p>foo <!-- this is a --\ncomment - with hyphens --></p>\n'
    )
    assert commonmark.render('foo <!--> foo -->\n') == '<p>foo <!--> foo --&gt;</p>\n'
    assert commonmark.render('foo <!---> foo -->\n') == '<p>foo <!---> foo --&gt;</p>\n'

    assert (
        gfm.render('foo <!-- not a comment -- two hyphens -->\n')
        == '<p>foo &lt;!-- not a comment -- two hyphens --&gt;</p>\n'
    )
    assert gfm.render('foo <!--> foo -->\n') == '<p>foo &lt;!--&gt; foo --&gt;</p>\n'


@pytest.mark.parametrize(
    ('markdown', 'html'),
    [
        ('*a***a*\n', '<p><em>a</em>*<em>a</em></p>\n'),
        ('*foo***bar*\n', '<p><em>foo</em>*<em>bar</em></p>\n'),
    ],
)
def test_emphasis_multiple_of_three_uses_original_delimiter_length(markdown: str, html: str) -> None:
    assert Wenmode().render(markdown) == html


def test_emphasis_respects_max_container_depth() -> None:
    app = Wenmode()
    app.parser.max_container_depth = 1

    assert app.render('****a****\n') == '<p>**<strong>a</strong>**</p>\n'


def test_long_emphasis_runs_do_not_exceed_container_depth() -> None:
    app = Wenmode()
    markdown = '*' * 1000 + 'a' + '*' * 1000 + '\n'

    root = app.parse(markdown)

    assert max_emphasis_depth(root) == app.parser.max_container_depth
    assert app.render_node(root).startswith('<p>' + '*' * 960)


def test_deep_link_label_brackets_do_not_recurse_before_destination_check() -> None:
    markdown = '[' * 1000 + 'a' + ']' * 1000 + '(/u)\n'

    html = Wenmode().render(markdown)

    assert html == '<p><a href="/u">' + '[' * 999 + 'a' + ']' * 999 + '</a></p>\n'


def test_image_alt_respects_max_container_depth() -> None:
    app = Wenmode()
    app.parser.max_container_depth = 1

    assert app.render('![![![a](/u)](/v)](/img)\n') == '<p><img src="/img" alt="![a](/u)" /></p>\n'


def test_deep_image_alt_does_not_recurse_unbounded() -> None:
    markdown = '![' * 1000 + 'a' + '](/u)' * 1000 + '\n'

    html = Wenmode().render(markdown)

    assert html.startswith('<p><img src="/u" alt="')
    assert html.endswith('" /></p>\n')


def max_emphasis_depth(node: Node) -> int:
    max_depth = 0
    stack: list[tuple[Node, int]] = [(node, 0)]
    while stack:
        item, parent_depth = stack.pop()
        if item.type in {'emphasis', 'strong'}:
            depth = parent_depth + 1
            max_depth = max(max_depth, depth)
        else:
            depth = parent_depth
        if isinstance(item, Parent):
            stack.extend((child, depth) for child in item.children)
    return max_depth


def test_parser_uses_first_inline_match_for_same_position() -> None:
    assert Wenmode([SearchInline, LaterSearchInline, TriggerInline]).render('x\n') == '<p>search</p>\n'
