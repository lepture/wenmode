from __future__ import annotations

import re
from typing import Any

from mkdocs.plugins import BasePlugin

from wenmode import HTMLRenderer, Wenmode
from wenmode.directives import Admonition, Details, Figure, TableOfContents
from wenmode.plugins import definition_list, fenced_directive, math
from wenmode.presets import github
from wenmode.rules import AtxHeading, ContainerDirective, LeafDirective, SetextHeading, TextDirective

FRONTMATTER_RE = re.compile(r'\A---[ \t]*\r?\n.*?\r?\n---[ \t]*(?:\r?\n|\Z)', re.DOTALL)
ADMONITION_NAMES = (
    'abstract',
    'bug',
    'caution',
    'danger',
    'example',
    'failure',
    'info',
    'note',
    'question',
    'quote',
    'success',
    'tip',
    'warning',
)


def create_wenmode() -> Wenmode:
    app = Wenmode(
        [
            TextDirective,
            LeafDirective,
            ContainerDirective,
            *github,
            AtxHeading(id_transform=True),
            SetextHeading(id_transform=True),
        ],
        renderer=HTMLRenderer(directives=[Admonition(names=ADMONITION_NAMES), Details(), Figure(), TableOfContents()]),
    )
    app.use(definition_list)
    app.use(fenced_directive)
    app.use(math)
    return app


def strip_frontmatter(markdown: str) -> str:
    return FRONTMATTER_RE.sub('', markdown, count=1)


def markdown_to_html(markdown: str) -> str:
    return create_wenmode().render(strip_frontmatter(markdown))


class WenmodePlugin(BasePlugin):
    def on_page_markdown(self, markdown: str, page: Any, config: Any, files: Any) -> str:
        return markdown_to_html(markdown)
