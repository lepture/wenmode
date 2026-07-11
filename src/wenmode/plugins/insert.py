from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Parent

from .._declarative import DeclarativePluginSpec, InlineDelimited, RendererFallback, RenderTemplate, install_declarative

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class InsertNode(Parent):
    """Inserted text node."""

    type: str = 'insert'


spec = DeclarativePluginSpec(
    name='insert',
    syntax=[
        InlineDelimited(
            name='insert',
            node=InsertNode,
            opener='^^',
            closer='^^',
            trigger_chars='^',
        )
    ],
    renderers={
        'html': {InsertNode.type: RenderTemplate('<ins>{children}</ins>')},
        'markdown': {InsertNode.type: RenderTemplate('^^{children}^^')},
        'rst': {InsertNode.type: RendererFallback('children')},
        'asciidoc': {InsertNode.type: RenderTemplate('[.underline]#{children}#')},
    },
)

nodes = [InsertNode]


def setup(wen: Wenmode, /) -> None:
    install_declarative(wen, spec)
