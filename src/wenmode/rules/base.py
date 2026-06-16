from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.nodes import Node
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


@dataclass
class Rule:
    name: str


@dataclass
class BlockRule(Rule):
    pattern: str

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Node | None:
        raise NotImplementedError


@dataclass
class InlineRule(Rule):
    pattern: str
    compiled: re.Pattern[str] = None  # type: ignore[assignment]

    def __post_init__(self) -> None:
        self.compiled = re.compile(self.pattern)

    def parse(self, parser: Wenmode, text: str, match: re.Match[str]) -> tuple[Node | None, int]:
        raise NotImplementedError
