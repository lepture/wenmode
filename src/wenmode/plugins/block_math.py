from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from wenmode.nodes import Literal, Node
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules.base import BlockRule, Rule
from wenmode.rules.blocks.util import collect_until
from wenmode.state import BlockState
from wenmode.utils import match_pattern

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


def render_html_math(renderer: HTMLRenderer, node: MathNode, context: HTMLRenderContext) -> str:
    return f'<div class="math math-display">{renderer.escape_html(node.value)}</div>\n'


def render_markdown_math(renderer: MarkdownRenderer, node: MathNode, context: RenderContext) -> str:
    if node.value.endswith('\n'):
        value = node.value
    else:
        value = node.value + '\n'
    return f'$$\n{value}$$\n\n'


def render_rst_math(renderer: RSTRenderer, node: MathNode, context: RSTRenderContext) -> str:
    if node.value.endswith('\n'):
        value = node.value
    else:
        value = node.value + '\n'
    return '.. math::\n\n' + indent_block(value.rstrip('\n'), '   ') + '\n\n'


def render_asciidoc_math(renderer: AsciiDocRenderer, node: MathNode, context: AsciiDocRenderContext) -> str:
    value = node.value.rstrip('\n')
    if value:
        return '[stem]\n++++\n' + value + '\n++++\n\n'
    return '[stem]\n++++\n++++\n\n'


nodes = [MathNode]
rules: list[type[Rule] | Rule] = [MathBlockRule]
handlers: RendererHandlers = {
    'html': {MathNode.type: render_html_math},
    'markdown': {MathNode.type: render_markdown_math},
    'rst': {MathNode.type: render_rst_math},
    'asciidoc': {MathNode.type: render_asciidoc_math},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
