from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Parent

from .._declarative import DeclarativePluginSpec, InlineDelimited, RendererFallback, RenderTemplate, install_declarative

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass
class InlineSpoilerNode(Parent):
    """Inline spoiler node."""

    type: str = 'inlineSpoiler'


spec = DeclarativePluginSpec(
    name='inline_spoiler',
    syntax=[
        InlineDelimited(
            name='inline_spoiler',
            node=InlineSpoilerNode,
            opener='>!',
            closer='!<',
            trigger_chars='>',
            allow_newline=False,
            reject_opening_whitespace=False,
            reject_closing_whitespace=False,
            reject_longer_run=False,
            strip_content=True,
        )
    ],
    renderers={
        'html': {InlineSpoilerNode.type: RenderTemplate('<span class="spoiler">{children}</span>')},
        'markdown': {InlineSpoilerNode.type: RenderTemplate('>! {children} !<')},
        'rst': {InlineSpoilerNode.type: RendererFallback('children')},
        'asciidoc': {InlineSpoilerNode.type: RenderTemplate('[.spoiler]#{children}#')},
    },
)

nodes = [InlineSpoilerNode]


def setup(wen: Wenmode, /) -> None:
    install_declarative(wen, spec)
