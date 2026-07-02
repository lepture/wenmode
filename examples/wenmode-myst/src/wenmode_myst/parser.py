from __future__ import annotations

from typing import Any

from docutils import nodes
from docutils.parsers.rst import Parser as RSTParser
from sphinx.application import Sphinx
from sphinx.parsers import Parser as SphinxParser

from wenmode import RSTRenderer, Wenmode
from wenmode.plugins import block_math, definition_list, frontmatter, inline_math, inline_role
from wenmode.plugins.fenced_directive import FencedDirectiveRule
from wenmode.presets import github

from . import target

LITERAL_BODY_DIRECTIVES = frozenset({'code-block', 'sourcecode'})
DIRECTIVE_FENCES = ('`', '~', ':')


wen = Wenmode(
    [
        FencedDirectiveRule(literal_names=LITERAL_BODY_DIRECTIVES, fence=DIRECTIVE_FENCES),
        *github,
    ],
    renderer=RSTRenderer(),
    plugins=[definition_list, frontmatter, inline_role, inline_math, block_math, target],
)


def markdown_to_rst(source: str) -> str:
    """Convert Markdown source to reStructuredText through Wenmode."""
    return wen.render(source)


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
