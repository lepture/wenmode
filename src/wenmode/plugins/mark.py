from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Parent

from .._declarative import DeclarativePluginSpec, InlineDelimited, RendererFallback, RenderTemplate, install_declarative

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class MarkNode(Parent):
    """Highlighted text node."""

    type: str = 'mark'


spec = DeclarativePluginSpec(
    name='mark',
    syntax=[
        InlineDelimited(
            name='mark',
            node=MarkNode,
            opener='==',
            closer='==',
            trigger_chars='=',
        )
    ],
    renderers={
        'html': {MarkNode.type: RenderTemplate('<mark>{children}</mark>')},
        'markdown': {MarkNode.type: RenderTemplate('=={children}==')},
        'rst': {MarkNode.type: RendererFallback('children')},
        'asciidoc': {MarkNode.type: RenderTemplate('#{children}#')},
    },
)

nodes = [MarkNode]


def setup(wen: Wenmode, /) -> None:
    install_declarative(wen, spec)
