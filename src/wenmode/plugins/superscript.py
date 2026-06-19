from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Node, Parent
from wenmode.plugins import RendererHandlers
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer
from wenmode.rules.base import InlineRule, Rule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


@dataclass
class SuperscriptNode(Parent):
    """Superscript node."""

    type: str = 'superscript'


class SuperscriptRule(InlineRule):
    """Parse caret-delimited superscript spans."""

    def __init__(self) -> None:
        super().__init__('superscript', r'\^(?:(?<!\\)(?:\\\\)*\\\^|\S|\\ )+?\^', '^')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        value = match.group(0)[1:-1].replace('\\ ', ' ')
        return SuperscriptNode(children=parser.parse_inlines(value, state)), match.end()


def render_html(renderer: HTMLRenderer, node: SuperscriptNode, context: HTMLRenderContext) -> str:
    return f'<sup>{renderer.render_children(node.children, context)}</sup>'


def render_markdown(renderer: MarkdownRenderer, node: SuperscriptNode, context: RenderContext) -> str:
    return f'^{renderer.render_script_children(node, "^", context)}^'


def render_rst(renderer: RSTRenderer, node: SuperscriptNode, context: RSTRenderContext) -> str:
    return f':sup:`{renderer.render_children(node.children, context)}`'


rules: list[type[Rule] | Rule] = [SuperscriptRule]
handlers: RendererHandlers = {
    'html': {'superscript': render_html},
    'markdown': {'superscript': render_markdown},
    'rst': {'superscript': render_rst},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
