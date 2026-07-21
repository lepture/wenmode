from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar

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
class SubscriptNode(Parent):
    """Subscript node."""

    type: str = 'subscript'


class SubscriptRule(InlineRule):
    """Parse tilde-delimited subscript spans."""

    order: ClassVar[int] = 90
    name = 'subscript'
    pattern = None
    trigger_chars = '~'

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        span = find_delimited_span(text, start, '~', reject_adjacent=True, allow_spaces=False, allow_escaped_space=True)
        if span is None:
            return None, start
        value = text[span.value_start : span.value_end].replace('\\ ', ' ')
        return SubscriptNode(children=parser.parse_inlines(value, state)), span.close_end


def render_html(renderer: HTMLRenderer, node: SubscriptNode, context: HTMLRenderContext) -> str:
    return f'<sub>{renderer.render_children(node.children, context)}</sub>'


def render_markdown(renderer: MarkdownRenderer, node: SubscriptNode, context: RenderContext) -> str:
    return f'~{renderer.render_script_children(node, "~", context)}~'


def render_rst(renderer: RSTRenderer, node: SubscriptNode, context: RSTRenderContext) -> str:
    return f':sub:`{renderer.render_children(node.children, context)}`'


def render_asciidoc(renderer: AsciiDocRenderer, node: SubscriptNode, context: AsciiDocRenderContext) -> str:
    return f'~{renderer.render_children(node.children, context)}~'


nodes = [SubscriptNode]
rules: list[type[Rule] | Rule] = [SubscriptRule]
handlers: RendererHandlers = {
    'html': {SubscriptNode.type: render_html},
    'markdown': {SubscriptNode.type: render_markdown},
    'rst': {SubscriptNode.type: render_rst},
    'asciidoc': {SubscriptNode.type: render_asciidoc},
}


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
