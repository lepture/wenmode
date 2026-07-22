from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Node, Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer
from wenmode.rules import InlineRule, Rule
from wenmode.rules.delimiters import find_delimited_span

from .._parser.state import BlockState
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
    opener = '^'

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        span = find_delimited_span(text, start, '^', allow_spaces=False, allow_escaped_space=True)
        if span is None:
            return None, start
        value = text[span.value_start : span.value_end].replace('\\ ', ' ')
        return SuperscriptNode(children=parser.parse_inlines(value, state)), span.close_end


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


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
