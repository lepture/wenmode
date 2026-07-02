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

from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


@dataclass
class SuperscriptNode(Parent):
    """Superscript node."""

    type: str = 'superscript'


class SuperscriptRule(InlineRule):
    """Parse caret-delimited superscript spans."""

    name = 'superscript'
    pattern = r'\^(?:(?<!\\)(?:\\\\)*\\\^|\S|\\ )+?\^'
    trigger_chars = '^'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        value = match.group(0)[1:-1].replace('\\ ', ' ')
        return SuperscriptNode(children=parser.parse_inlines(value, state)), match.end()


def render_html(renderer: HTMLRenderer, node: SuperscriptNode, context: HTMLRenderContext) -> str:
    return f'<sup>{renderer.render_children(node.children, context)}</sup>'


def render_markdown(renderer: MarkdownRenderer, node: SuperscriptNode, context: RenderContext) -> str:
    return f'^{renderer.render_script_children(node, "^", context)}^'


def render_rst(renderer: RSTRenderer, node: SuperscriptNode, context: RSTRenderContext) -> str:
    return f':sup:`{renderer.render_children(node.children, context)}`'


def render_asciidoc(renderer: AsciiDocRenderer, node: SuperscriptNode, context: AsciiDocRenderContext) -> str:
    return f'^{renderer.render_children(node.children, context)}^'


nodes = [SuperscriptNode]
rules: list[type[Rule] | Rule] = [SuperscriptRule]
handlers: RendererHandlers = {
    'html': {SuperscriptNode.type: render_html},
    'markdown': {SuperscriptNode.type: render_markdown},
    'rst': {SuperscriptNode.type: render_rst},
    'asciidoc': {SuperscriptNode.type: render_asciidoc},
}


def setup(wen: Wenmode, **options: Any) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
