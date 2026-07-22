from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, ClassVar, Literal

from wenmode.nodes import Blockquote as BlockquoteNode
from wenmode.nodes import Parent
from wenmode.renderers import MarkdownRenderer, RenderContext
from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.html import HTMLRenderContext, HTMLRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer, indent_block
from wenmode.rules import BlockCandidate, Blockquote, BlockRule

from .._parser.source import SourceMap
from .._parser.state import BlockState
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.parser import Parser


DEFAULT_ALERT_TITLES = {
    'note': 'Note',
    'tip': 'Tip',
    'important': 'Important',
    'warning': 'Warning',
    'caution': 'Caution',
}
ALERT_NAME_RE = re.compile(r'^[A-Za-z][A-Za-z0-9_-]*$')
HtmlStyle = Literal['github', 'admonition']


@dataclass
class GithubAlertNode(Parent):
    """GitHub alert container node."""

    name: str = ''
    block: ClassVar[bool] = True
    type: str = 'githubAlert'


class GithubAlertBlockquote(BlockRule):
    """Parse GitHub alert blockquotes when the blockquote rule is enabled."""
    name = Blockquote.name
    pattern = Blockquote.pattern

    def __init__(self, alerts: Mapping[str, str]) -> None:
        super().__init__()
        self.alerts = dict(alerts)
        names = '|'.join(re.escape(name) for name in sorted(self.alerts, key=len, reverse=True))
        self.alert_re = re.compile(rf'^\[!(?P<name>{names})](?:[ \t]*(?:\r?\n|$))', re.I)

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> BlockquoteNode | GithubAlertNode:
        source = state.source.collect()
        text = Blockquote.parse_text(parser, state, source)
        source_map = source.map()
        if state.depth == 0:
            alert = parse_alert(text, source_map, self.alert_re)
            if alert is not None:
                name, body_text, body_source = alert
                return GithubAlertNode(
                    name=name,
                    children=parser.parse_blocks(body_text, parent_state=state, source=body_source),
                )
        return BlockquoteNode(children=parser.parse_blocks(text, parent_state=state, source=source_map))


def parse_alert(
    text: str, source: SourceMap | None, alert_re: re.Pattern[str]
) -> tuple[str, str, SourceMap | None] | None:
    match = alert_re.match(text)
    if match is None:
        return None
    body_start = match.end()
    body_text = text[body_start:]
    body_source = source.slice(body_start, len(text)) if source is not None else None
    return match.group('name').lower(), body_text, body_source


def render_html_alert(renderer: HTMLRenderer, node: GithubAlertNode, context: HTMLRenderContext) -> str:
    return render_github_html_alert(renderer, node, context)


def render_github_html_alert(
    renderer: HTMLRenderer,
    node: GithubAlertNode,
    context: HTMLRenderContext,
    alert_titles: Mapping[str, str] = DEFAULT_ALERT_TITLES,
) -> str:
    name = renderer.escape_html(node.name)
    title = renderer.escape_html(alert_titles[node.name])
    return (
        f'<div class="markdown-alert markdown-alert-{name}">\n'
        f'<p class="markdown-alert-title">{title}</p>\n'
        f'{renderer.render_children(node.children, context)}'
        '</div>\n'
    )


def render_admonition_html_alert(
    renderer: HTMLRenderer,
    node: GithubAlertNode,
    context: HTMLRenderContext,
    alert_titles: Mapping[str, str] = DEFAULT_ALERT_TITLES,
) -> str:
    name = renderer.escape_html(node.name)
    title = renderer.escape_html(alert_titles[node.name])
    return (
        f'<aside class="admonition admonition-{name}">\n'
        f'<p class="admonition-title">{title}</p>\n'
        f'{renderer.render_children(node.children, context)}'
        '</aside>\n'
    )


def render_markdown_alert(renderer: MarkdownRenderer, node: GithubAlertNode, context: RenderContext) -> str:
    marker = f'> [!{node.name.upper()}]'
    body = renderer.render_children(node.children, context).rstrip('\n')
    if not body:
        return marker + '\n\n'
    lines = body.splitlines()
    prefixed = [f'> {line}' if line else '>' for line in lines]
    return marker + '\n' + '\n'.join(prefixed) + '\n\n'


def render_rst_alert(renderer: RSTRenderer, node: GithubAlertNode, context: RSTRenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    directive = '.. ' + node.name + '::'
    if not body:
        return directive + '\n\n'
    return directive + '\n\n' + indent_block(body, '   ') + '\n\n'


def render_asciidoc_alert(renderer: AsciiDocRenderer, node: GithubAlertNode, context: AsciiDocRenderContext) -> str:
    body = renderer.render_children(node.children, context).rstrip('\n')
    marker = f'[{node.name.upper()}]'
    if not body:
        return marker + '\n====\n====\n\n'
    return marker + '\n====\n' + body + '\n====\n\n'


nodes = [GithubAlertNode]
handlers: RendererHandlers = {
    'html': {GithubAlertNode.type: render_html_alert},
    'markdown': {GithubAlertNode.type: render_markdown_alert},
    'rst': {GithubAlertNode.type: render_rst_alert},
    'asciidoc': {GithubAlertNode.type: render_asciidoc_alert},
}


@dataclass(frozen=True)
class GithubAlertPlugin:
    html_style: HtmlStyle = 'github'
    alerts: Mapping[str, str] | None = None

    def setup(self, wen: Wenmode, /) -> None:
        alert_titles = normalize_alert_titles(self.alerts)
        rule = wen.parser.rules.get('blockquote')
        if isinstance(rule, Blockquote | GithubAlertBlockquote):
            replacement = GithubAlertBlockquote(alert_titles)
            replacement.root_transforms = list(rule.root_transforms)
            replacement.node_transforms = list(rule.node_transforms)
            wen.register_rule(replacement)

        configured_handlers = build_handlers(alert_titles, self.html_style)
        wen.register_renderer_handlers(configured_handlers)


def build_handlers(alert_titles: Mapping[str, str], html_style: HtmlStyle) -> RendererHandlers:
    if html_style == 'github':
        def render_html(renderer: HTMLRenderer, node: GithubAlertNode, context: HTMLRenderContext) -> str:
            return render_github_html_alert(renderer, node, context, alert_titles)
    else:
        def render_html(renderer: HTMLRenderer, node: GithubAlertNode, context: HTMLRenderContext) -> str:
            return render_admonition_html_alert(renderer, node, context, alert_titles)
    return {
        **handlers,
        'html': {GithubAlertNode.type: render_html},
    }


def configure(*, html_style: HtmlStyle = 'github', alerts: Mapping[str, str] | None = None) -> GithubAlertPlugin:
    validate_html_style(html_style)
    normalize_alert_titles(alerts)
    return GithubAlertPlugin(html_style=html_style, alerts=alerts)


def normalize_alert_titles(alerts: Mapping[str, str] | None) -> dict[str, str]:
    titles = dict(DEFAULT_ALERT_TITLES)
    if alerts is None:
        return titles

    for name, title in alerts.items():
        normalized = name.lower()
        if ALERT_NAME_RE.fullmatch(name) is None:
            raise ValueError('alert names must match [A-Za-z][A-Za-z0-9_-]*')
        if not isinstance(title, str) or not title:
            raise ValueError('alert titles must be non-empty strings')
        titles[normalized] = title
    return titles


def setup(wen: Wenmode, /) -> None:
    configure().setup(wen)


def validate_html_style(html: str) -> None:
    if html not in {'github', 'admonition'}:
        raise ValueError("html_style must be 'github' or 'admonition'")
