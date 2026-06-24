from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ClassVar

from wenmode import RSTRenderer
from wenmode.nodes import Node
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode import Wenmode

TARGET_RE = re.compile(r'[ \t]{0,3}\((?P<label>[^)\r\n]+)\)=[ \t]*(?:\r?\n)?$')


@dataclass
class TargetNode(Node):
    """A MyST ``(label)=`` target rendered as a reStructuredText target."""

    label: str = ''
    type: str = 'mystTarget'


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


def render_target(renderer: RSTRenderer, node: TargetNode, context: Any) -> str:
    return f'.. _{node.label}:\n\n'


handlers = {'rst': {'mystTarget': render_target}}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rule(TargetRule)
    wenmode.register_renderer_handlers(handlers)
