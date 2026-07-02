from __future__ import annotations

from dataclasses import dataclass

from wenmode.nodes import Parent

from .._declarative import DeclarativePluginSpec, InlineDelimited, RenderTemplate


@dataclass
class InlineSpoilerNode(Parent):
    """Inline spoiler node."""

    type: str = 'inlineSpoiler'


spec = DeclarativePluginSpec(
    name='inline_spoiler',
    nodes=[InlineSpoilerNode],
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
        'rst': {InlineSpoilerNode.type: RenderTemplate('{children}')},
        'asciidoc': {InlineSpoilerNode.type: RenderTemplate('[.spoiler]#{children}#')},
    },
)

nodes = spec.nodes
