from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, ClassVar

from wenmode.nodes import Link as LinkNode
from wenmode.nodes import Node
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer
from wenmode.rules.base import InlineRule, Rule
from wenmode.rules.inlines.link import (
    closing_bracket_cache,
    find_closing_bracket,
    invalid_reference_label,
    parse_direct_destination,
)
from wenmode.rules.references import resolve_state_reference
from wenmode.state import BlockState

from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser

RUBY_PATTERN = r'\[(?:\w+\([\w ]+\))+\]'
RUBY_SEGMENT_RE = re.compile(r'(\w+)\(([\w ]+)\)')


@dataclass
class RubyNode(Node):
    """Ruby annotation node."""

    segments: list[dict[str, str]] = field(default_factory=list)
    type: str = 'ruby'


class RubyRule(InlineRule):
    """Parse ruby annotation syntax."""

    order: ClassVar[int] = 90
    name = 'ruby'
    pattern = RUBY_PATTERN
    trigger_chars = '['

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        ruby = RubyNode(segments=parse_ruby_segments(match.group(0)))
        source = parser.inline_source(text, state, match.start(), match.end())
        if source is not None:
            ruby.position = source.position(0, match.end() - match.start())
        end = match.end()
        link = parse_ruby_link(parser, text, end, ruby, state)
        if link is not None:
            return link
        return ruby, end


def parse_ruby_segments(value: str) -> list[dict[str, str]]:
    return [{'base': match.group(1), 'text': match.group(2)} for match in RUBY_SEGMENT_RE.finditer(value[1:-1])]


def parse_ruby_link(
    parser: Parser, text: str, start: int, ruby: RubyNode, state: BlockState
) -> tuple[Node, int] | None:
    if 'link' not in parser.rules or start >= len(text):
        return None

    if text[start] == '(':
        direct = parse_direct_destination(text, start)
        if direct is None:
            return None
        url, title, end = direct
        return LinkNode(url=url, title=title, children=[ruby]), end

    if text[start] != '[':
        return None

    ref_end = find_closing_bracket(text, start + 1, closing_bracket_cache(state))
    if ref_end is None:
        return None

    label = text[start + 1 : ref_end]
    if not label or invalid_reference_label(label):
        return None

    reference = resolve_state_reference(state, label)
    if reference:
        return LinkNode(url=reference.url, title=reference.title, children=[ruby]), ref_end + 1
    return None


def render_html(renderer: HTMLRenderer, node: RubyNode, context: HTMLRenderContext) -> str:
    content = ''.join(
        f'{renderer.escape_html(segment["base"])}<rt>{renderer.escape_html(segment["text"])}</rt>'
        for segment in node.segments
    )
    return f'<ruby>{content}</ruby>'


def render_markdown(renderer: MarkdownRenderer, node: RubyNode, context: RenderContext) -> str:
    segments = ''.join(f'{segment["base"]}({segment["text"]})' for segment in node.segments)
    return f'[{segments}]'


def render_rst(renderer: RSTRenderer, node: RubyNode, context: RSTRenderContext) -> str:
    return ''.join(
        f'{renderer.escape_text(segment["base"])} ({renderer.escape_text(segment["text"])})'
        for segment in node.segments
    )


nodes = {RubyNode.type: RubyNode}
rules: list[type[Rule] | Rule] = [RubyRule]
handlers: RendererHandlers = {
    'html': {RubyNode.type: render_html},
    'markdown': {RubyNode.type: render_markdown},
    'rst': {RubyNode.type: render_rst},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
