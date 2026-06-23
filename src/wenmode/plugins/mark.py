from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Node, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
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
class MarkNode(Parent):
    """Highlighted text node."""

    type: str = 'mark'


class MarkRule(InlineRule):
    """Parse highlighted text delimited by ``==``."""

    name = 'mark'
    pattern = r'==(?=[^\s=])'
    trigger_chars = '='

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        start = match.start()
        if is_part_of_longer_run(text, start, '='):
            return None, start

        close = find_closing_marker(text, match.end(), '=')
        if close == -1:
            return None, start

        value_start = match.end()
        value = text[value_start:close]
        return MarkNode(
            children=parser.parse_inlines(value, state, source=parser.inline_source(text, state, value_start, close))
        ), close + 2


def render_html(renderer: HTMLRenderer, node: MarkNode, context: HTMLRenderContext) -> str:
    return f'<mark>{renderer.render_children(node.children, context)}</mark>'


def render_markdown(renderer: MarkdownRenderer, node: MarkNode, context: RenderContext) -> str:
    return f'=={renderer.render_children(node.children, context)}=='


def render_rst(renderer: RSTRenderer, node: MarkNode, context: RSTRenderContext) -> str:
    return renderer.render_children(node.children, context)


rules: list[type[Rule] | Rule] = [MarkRule]
handlers: RendererHandlers = {
    'html': {'mark': render_html},
    'markdown': {'mark': render_markdown},
    'rst': {'mark': render_rst},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
