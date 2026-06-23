from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Literal, Node
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules.base import BlockRule, InlineRule, Rule
from wenmode.rules.blocks.util import collect_until
from wenmode.state import BlockState
from wenmode.utils import is_escaped, match_pattern

from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

MATH_OPENER_RE = re.compile(r'^[ \t]{0,3}\$\$[ \t]*')
MATH_CLOSER_RE = re.compile(r'^[ \t]{0,3}\$\$[ \t]*(?:\r?\n)?$')


@dataclass
class MathNode(Literal):
    """Display math block node."""

    type: str = 'math'


@dataclass
class InlineMathNode(Literal):
    """Inline math node."""

    type: str = 'inlineMath'


class MathBlockRule(BlockRule):
    """Parse display math blocks fenced by ``$$`` markers."""

    name = 'math_block'
    pattern = r'[ \t]{0,3}\$\$'

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node:
        rest = parse_math_opener(state.line)
        if rest is None:  # pragma: no cover - block opener already matched
            rest = ''
        lines: list[str] = []
        if rest:
            lines.append(rest + '\n')
        state.advance()
        lines.extend(collect_until(state, lambda line: match_pattern(MATH_CLOSER_RE, line)))
        return MathNode(value=''.join(lines))


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


def parse_math_opener(line: str) -> str | None:
    text = line
    if text.endswith('\n'):
        text = text[:-1]
        if text.endswith('\r'):
            text = text[:-1]

    match = MATH_OPENER_RE.match(text)
    if match is None:
        return None
    return text[match.end() :]


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


def render_html_math(renderer: HTMLRenderer, node: MathNode, context: HTMLRenderContext) -> str:
    return f'<div class="math math-display">{renderer.escape_html(node.value)}</div>\n'


def render_html_inline_math(renderer: HTMLRenderer, node: InlineMathNode, context: HTMLRenderContext) -> str:
    return f'<span class="math math-inline">{renderer.escape_html(node.value)}</span>'


def render_markdown_math(renderer: MarkdownRenderer, node: MathNode, context: RenderContext) -> str:
    if node.value.endswith('\n'):
        value = node.value
    else:
        value = node.value + '\n'
    return f'$$\n{value}$$\n\n'


def render_markdown_inline_math(renderer: MarkdownRenderer, node: InlineMathNode, context: RenderContext) -> str:
    return f'${node.value}$'


def render_rst_math(renderer: RSTRenderer, node: MathNode, context: RSTRenderContext) -> str:
    if node.value.endswith('\n'):
        value = node.value
    else:
        value = node.value + '\n'
    return '.. math::\n\n' + indent_block(value.rstrip('\n'), '   ') + '\n\n'


def render_rst_inline_math(renderer: RSTRenderer, node: InlineMathNode, context: RSTRenderContext) -> str:
    return f':math:`{renderer.escape_inline_literal(node.value)}`'


rules: list[type[Rule] | Rule] = [MathBlockRule, InlineMathRule]
handlers: RendererHandlers = {
    'html': {'math': render_html_math, 'inlineMath': render_html_inline_math},
    'markdown': {'math': render_markdown_math, 'inlineMath': render_markdown_inline_math},
    'rst': {'math': render_rst_math, 'inlineMath': render_rst_inline_math},
}


def setup(wenmode: Wenmode, block: bool = True, inline: bool = True, **options: Any) -> None:
    selected_rules: list[type[Rule] | Rule] = []
    if block:
        selected_rules.append(MathBlockRule)
    if inline:
        selected_rules.append(InlineMathRule)
    wenmode.register_rules(selected_rules)
    wenmode.register_renderer_handlers(handlers)
