from __future__ import annotations

import re

import pytest

from wenmode import HTMLRenderer, MarkdownRenderer, Parser, Wenmode
from wenmode.directives import Figure
from wenmode.nodes import Node, Text
from wenmode.rules import (
    AtxHeading,
    InlineRule,
    RawHtml,
)
from wenmode.state import BlockState


class SearchInline(InlineRule):
    order = 10

    def __init__(self) -> None:
        super().__init__('search_inline', r'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='search'), match.end()


class LaterSearchInline(InlineRule):
    order = 20

    def __init__(self) -> None:
        super().__init__('later_search_inline', r'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='later'), match.end()


class TriggerInline(InlineRule):
    order = 30

    def __init__(self) -> None:
        super().__init__('trigger_inline', r'x', 'x')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value='trigger'), match.end()


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


def test_parser_uses_first_inline_match_for_same_position() -> None:
    assert Wenmode([SearchInline, LaterSearchInline, TriggerInline]).render('x\n') == '<p>search</p>\n'
