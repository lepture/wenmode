from __future__ import annotations

from typing import Any

from mkdocs.plugins import BasePlugin

from wenmode import HTMLRenderer, Wenmode
from wenmode.directives import Admonition, Details, Figure, TableOfContents
from wenmode.plugins import definition_list, fenced_directive, frontmatter, math
from wenmode.presets import github
from wenmode.rules import AtxHeading, ContainerDirective, LeafDirective, SetextHeading, TextDirective

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
        plugins=[definition_list, fenced_directive, frontmatter, math],
    )
    return app


def markdown_to_html(markdown: str) -> str:
    return create_wenmode().render(markdown)


class WenmodePlugin(BasePlugin):
    def on_page_markdown(self, markdown: str, page: Any, config: Any, files: Any) -> str:
        return markdown_to_html(markdown)
