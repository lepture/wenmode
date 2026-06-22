from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, ClassVar

from docutils import nodes
from docutils.parsers.rst import Parser as RSTParser
from sphinx.application import Sphinx
from sphinx.parsers import Parser as SphinxParser

from wenmode import RSTRenderer, Wenmode
from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import Node
from wenmode.plugins import definition_list, frontmatter, inline_role, math
from wenmode.plugins.fenced_directive import (
    FENCED_DIRECTIVE_RE,
    FencedDirectiveRule,
)
from wenmode.plugins.types import RendererHandlers
from wenmode.presets import github
from wenmode.renderers.rst import indent_block, render_directive_options
from wenmode.rules import ContainerDirective, LeafDirective, TextDirective
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

TARGET_RE = re.compile(r'[ \t]{0,3}\((?P<label>[^)\r\n]+)\)=[ \t]*(?:\r?\n)?$')
COLON_FENCE_RE = re.compile(r'(?P<indent>[ \t]{0,3})(?P<fence>:{3,})\{(?P<name>[A-Za-z][A-Za-z0-9_-]*)}(?P<title>.*)$')
LITERAL_BODY_DIRECTIVES = frozenset({'code-block', 'sourcecode'})


@dataclass
class TargetNode(Node):
    """A MyST ``(label)=`` target rendered as a reStructuredText target."""

    label: str = ''
    type: str = 'mystTarget'


@dataclass
class RSTDirectiveNode(Node):
    """A local raw-body directive used for MyST-to-reStructuredText bridging."""

    name: str = ''
    argument: str = ''
    attributes: dict[str, str] | None = None
    body: str = ''
    type: str = 'rstDirective'


class TargetRule(BlockRule):
    """Parse MyST-style block targets such as ``(usage)=``."""

    order: ClassVar[int] = 20

    def __init__(self) -> None:
        super().__init__('myst_target', r'[ \t]{0,3}\([^)]+\)=[ \t]*(?:\r?\n)?$')

    def parse(self, parser: Any, state: BlockState, match: re.Match[str]) -> Node | None:
        target = TARGET_RE.match(state.line)
        if target is None:
            return None
        state.advance()
        return TargetNode(label=target.group('label').strip())


class RSTFencedDirectiveRule(FencedDirectiveRule):
    """Parse MyST fenced directives, keeping selected directive bodies raw."""

    directive_head_re = FENCED_DIRECTIVE_RE

    def parse(self, parser: Any, state: BlockState, match: re.Match[str]) -> Node | None:
        name, title, closer = self.parse_directive_head(state, self.directive_head_re)
        attributes = self.parse_directive_attributes(state)
        if name in LITERAL_BODY_DIRECTIVES:
            lines = collect_until(state, lambda line: closer.match(line.rstrip('\r\n')) is not None)
            return RSTDirectiveNode(
                name=name,
                argument=title or '',
                attributes=attributes or None,
                body=''.join(lines),
            )

        children = self.parse_directive_body(parser, state, title, closer)
        return ContainerDirectiveNode(name=name, attributes=attributes or None, children=children)


class ColonFenceDirectiveRule(RSTFencedDirectiveRule):
    """Parse MyST ``colon_fence`` directives such as ``:::{note} Title``."""

    name = 'myst_colon_fence'
    pattern = r'[ \t]{0,3}:{3,}\{[A-Za-z][A-Za-z0-9_-]*}'
    directive_head_re = COLON_FENCE_RE


def collect_until(state: BlockState, is_closer: Any) -> list[str]:
    lines: list[str] = []
    while not state.done:
        line = state.line
        if is_closer(line):
            state.advance()
            break
        lines.append(line)
        state.advance()
    return lines


def render_target(renderer: RSTRenderer, node: TargetNode, context: Any) -> str:
    return f'.. _{node.label}:\n\n'


def render_rst_directive(renderer: RSTRenderer, node: RSTDirectiveNode, context: Any) -> str:
    head = f'.. {node.name}::'
    if node.argument:
        head += f' {node.argument}'
    options = render_directive_options(node.attributes)
    body = node.body.rstrip('\n')

    if not body:
        if options:
            return '\n'.join([head, *options]) + '\n\n'
        return head + '\n\n'

    lines = [head, *options, '', indent_block(body, '   ')]
    return '\n'.join(lines) + '\n\n'


handlers: RendererHandlers = {
    'rst': {
        'mystTarget': render_target,
        'rstDirective': render_rst_directive,
    }
}


def markdown_to_rst(source: str) -> str:
    """Convert Markdown source to reStructuredText through Wenmode."""
    return create_wenmode().render(source)


def create_wenmode() -> Wenmode:
    app = Wenmode(
        [
            TargetRule,
            RSTFencedDirectiveRule,
            ColonFenceDirectiveRule,
            TextDirective,
            LeafDirective,
            ContainerDirective,
            *github,
        ],
        renderer=RSTRenderer(),
    )
    app.use(definition_list)
    app.use(frontmatter)
    app.use(inline_role)
    app.use(math)
    app.register_renderer_handlers(handlers)
    return app


class WenmodeMystParser(SphinxParser):
    """Sphinx source parser for the local Wenmode/MyST bridge."""

    supported = ('md', 'markdown', 'myst')
    settings_spec = RSTParser.settings_spec
    config_section = 'wenmode myst parser'
    config_section_dependencies = ('parsers',)
    translate_section_name = None

    def parse(self, inputstring: str, document: nodes.document) -> None:
        rst = markdown_to_rst(inputstring)
        RSTParser().parse(rst, document)


def setup(app: Sphinx) -> dict[str, Any]:
    app.add_source_parser(WenmodeMystParser, override=True)
    app.add_source_suffix('.md', 'markdown', override=True)
    return {
        'version': '0.1.0',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
