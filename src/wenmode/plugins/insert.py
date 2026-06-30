from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Node, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer
from wenmode.rules.base import InlineRule, Rule
from wenmode.state import BlockState

from ._formatting import find_closing_marker, is_part_of_longer_run
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


@dataclass
class InsertNode(Parent):
    """Inserted text node."""

    type: str = 'insert'


class InsertRule(InlineRule):
    """Parse inserted text delimited by ``^^``."""

    name = 'insert'
    pattern = r'\^\^(?=[^\s\^])'
    trigger_chars = '^'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        start = match.start()
        if is_part_of_longer_run(text, start, '^'):
            return None, start

        close = find_closing_marker(text, match.end(), '^')
        if close == -1:
            return None, start

        value_start = match.end()
        value = text[value_start:close]
        return InsertNode(
            children=parser.parse_inlines(value, state, source=parser.inline_source(text, state, value_start, close))
        ), close + 2


def render_html(renderer: HTMLRenderer, node: InsertNode, context: HTMLRenderContext) -> str:
    return f'<ins>{renderer.render_children(node.children, context)}</ins>'


def render_markdown(renderer: MarkdownRenderer, node: InsertNode, context: RenderContext) -> str:
    return f'^^{renderer.render_children(node.children, context)}^^'


def render_rst(renderer: RSTRenderer, node: InsertNode, context: RSTRenderContext) -> str:
    return renderer.render_children(node.children, context)


def render_asciidoc(renderer: AsciiDocRenderer, node: InsertNode, context: AsciiDocRenderContext) -> str:
    return f'[.underline]#{renderer.render_children(node.children, context)}#'


nodes = {InsertNode.type: InsertNode}
rules: list[type[Rule] | Rule] = [InsertRule]
handlers: RendererHandlers = {
    'html': {InsertNode.type: render_html},
    'markdown': {InsertNode.type: render_markdown},
    'rst': {InsertNode.type: render_rst},
    'asciidoc': {InsertNode.type: render_asciidoc},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
