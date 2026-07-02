from __future__ import annotations

from dataclasses import dataclass

from wenmode.nodes import Parent

from .._declarative import DeclarativePluginSpec, InlineDelimited, RenderTemplate


@dataclass
class InsertNode(Parent):
    """Inserted text node."""

    type: str = 'insert'


spec = DeclarativePluginSpec(
    name='insert',
    nodes=[InsertNode],
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
        'rst': {InsertNode.type: RenderTemplate('{children}')},
        'asciidoc': {InsertNode.type: RenderTemplate('[.underline]#{children}#')},
    },
)

nodes = spec.nodes
