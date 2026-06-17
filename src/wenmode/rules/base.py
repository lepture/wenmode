from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, ClassVar

from wenmode.nodes import Node
from wenmode.state import BlockState

from .transforms import RootTransform

if TYPE_CHECKING:
    from wenmode.parser import Parser


@dataclass
class Rule:
    name: str
    order: ClassVar[int] = 100
    root_transforms: list[RootTransform] = field(init=False, default_factory=list)


@dataclass
class BlockRule(Rule):
    pattern: str

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        raise NotImplementedError


@dataclass
class ContinueRule(Rule):
    def parse_paragraph_continuation(self, parser: Parser, state: BlockState, lines: list[str]) -> Node | None:
        raise NotImplementedError


@dataclass
class InlineRule(Rule):
    pattern: str
    trigger_chars: str = ''
    compiled: re.Pattern[str] = field(init=False)

    def __post_init__(self) -> None:
        self.compiled = re.compile(self.pattern)

    def search(self, text: str, pos: int = 0) -> re.Match[str] | None:
        return self.compiled.search(text, pos)

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        raise NotImplementedError
