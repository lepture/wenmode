from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

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
class SubscriptNode(Parent):
    """Subscript node."""

    type: str = 'subscript'


class SubscriptRule(InlineRule):
    """Parse tilde-delimited subscript spans."""

    order: ClassVar[int] = 90
    name = 'subscript'
    pattern = r'(?<!~)~(?!~)(?:(?<!\\)(?:\\\\)*\\~|[^\s~]|\\ )+?(?<!~)~(?!~)'
    trigger_chars = '~'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        value = match.group(0)[1:-1].replace('\\ ', ' ')
        return SubscriptNode(children=parser.parse_inlines(value, state)), match.end()


def render_html(renderer: HTMLRenderer, node: SubscriptNode, context: HTMLRenderContext) -> str:
    return f'<sub>{renderer.render_children(node.children, context)}</sub>'


def render_markdown(renderer: MarkdownRenderer, node: SubscriptNode, context: RenderContext) -> str:
    return f'~{renderer.render_script_children(node, "~", context)}~'


def render_rst(renderer: RSTRenderer, node: SubscriptNode, context: RSTRenderContext) -> str:
    return f':sub:`{renderer.render_children(node.children, context)}`'


def render_asciidoc(renderer: AsciiDocRenderer, node: SubscriptNode, context: AsciiDocRenderContext) -> str:
    return f'~{renderer.render_children(node.children, context)}~'


nodes = {SubscriptNode.type: SubscriptNode}
rules: list[type[Rule] | Rule] = [SubscriptRule]
handlers: RendererHandlers = {
    'html': {SubscriptNode.type: render_html},
    'markdown': {SubscriptNode.type: render_markdown},
    'rst': {SubscriptNode.type: render_rst},
    'asciidoc': {SubscriptNode.type: render_asciidoc},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
