from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BlockState:
    lines: list[str]
    index: int = 0

    @classmethod
    def from_text(cls, text: str) -> BlockState:
        return cls(text.splitlines(keepends=True))

    @property
    def done(self) -> bool:
        return self.index >= len(self.lines)

    @property
    def line(self) -> str:
        return self.lines[self.index]

    def advance(self, count: int = 1) -> None:
        self.index += count
