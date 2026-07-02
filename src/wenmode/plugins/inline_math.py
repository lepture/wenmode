from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Literal, Node
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer
from wenmode.rules.base import InlineRule, Rule
from wenmode.state import BlockState
from wenmode.utils import is_escaped

from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


@dataclass
class InlineMathNode(Literal):
    """Inline math node."""

    type: str = 'inlineMath'


class InlineMathRule(InlineRule):
    """Parse inline math delimited by dollar signs."""

    name = 'inline_math'
    pattern = r'\$'
    trigger_chars = '$'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        start = match.start()
        if is_escaped(text, start) or is_adjacent_to_dollar(text, start) or is_opening_space(text, start):
            return None, start

        end = find_closing_dollar(text, match.end())
        if end is None:
            return None, start

        value = text[match.end() : end]
        if value.strip() == '':
            return None, start
        return InlineMathNode(value=value), end + 1


def find_closing_dollar(text: str, start: int) -> int | None:
    index = start
    while index < len(text):
        char = text[index]
        if char in '\r\n':
            return None
        if char == '$' and not is_escaped(text, index) and not is_adjacent_closing_dollar(text, index):
            if is_closing_space(text, index) or is_closing_before_digit(text, index):
                index += 1
                continue
            return index
        index += 1
    return None


def is_opening_space(text: str, index: int) -> bool:
    return index + 1 >= len(text) or text[index + 1].isspace()


def is_closing_space(text: str, index: int) -> bool:
    return index == 0 or text[index - 1].isspace()


def is_closing_before_digit(text: str, index: int) -> bool:
    return index + 1 < len(text) and text[index + 1].isdigit()


def is_adjacent_closing_dollar(text: str, index: int) -> bool:
    previous_is_unescaped_dollar = index > 0 and text[index - 1] == '$' and not is_escaped(text, index - 1)
    next_is_dollar = index + 1 < len(text) and text[index + 1] == '$'
    return previous_is_unescaped_dollar or next_is_dollar


def is_adjacent_to_dollar(text: str, index: int) -> bool:
    previous_is_dollar = index > 0 and text[index - 1] == '$'
    next_is_dollar = index + 1 < len(text) and text[index + 1] == '$'
    return previous_is_dollar or next_is_dollar


def render_html_inline_math(renderer: HTMLRenderer, node: InlineMathNode, context: HTMLRenderContext) -> str:
    return f'<span class="math math-inline">{renderer.escape_html(node.value)}</span>'


def render_markdown_inline_math(renderer: MarkdownRenderer, node: InlineMathNode, context: RenderContext) -> str:
    return f'${node.value}$'


def render_rst_inline_math(renderer: RSTRenderer, node: InlineMathNode, context: RSTRenderContext) -> str:
    return f':math:`{renderer.escape_interpreted_text(node.value)}`'


def render_asciidoc_inline_math(
    renderer: AsciiDocRenderer, node: InlineMathNode, context: AsciiDocRenderContext
) -> str:
    return f'stem:[{node.value}]'


nodes = [InlineMathNode]
rules: list[type[Rule] | Rule] = [InlineMathRule]
handlers: RendererHandlers = {
    'html': {InlineMathNode.type: render_html_inline_math},
    'markdown': {InlineMathNode.type: render_markdown_inline_math},
    'rst': {InlineMathNode.type: render_rst_inline_math},
    'asciidoc': {InlineMathNode.type: render_asciidoc_inline_math},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
