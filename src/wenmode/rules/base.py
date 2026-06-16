from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import Node
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


@dataclass
class Rule:
    name: str
    has_references: ClassVar[bool] = False

    def parse_paragraph_continuation(
        self, parser: Wenmode, state: BlockState, lines: list[str]
    ) -> Node | None:
        return None


@dataclass
class BlockRule(Rule):
    pattern: str

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Node | None:
        raise NotImplementedError


@dataclass
class InlineRule(Rule):
    pattern: str
    trigger_chars: str = ''
    compiled: re.Pattern[str] = field(init=False)

    def __post_init__(self) -> None:
        self.compiled = re.compile(self.pattern)

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        raise NotImplementedError
