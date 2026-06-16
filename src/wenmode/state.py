from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Reference:
    url: str
    title: str | None = None


@dataclass
class BlockState:
    lines: list[str]
    index: int = 0
    references: dict[str, Reference] = field(default_factory=dict)
    depth: int = 0

    @classmethod
    def from_text(
        cls, text: str, references: dict[str, Reference] | None = None, depth: int = 0
    ) -> BlockState:
        return cls(text.splitlines(keepends=True), references=references if references is not None else {}, depth=depth)

    @property
    def done(self) -> bool:
        return self.index >= len(self.lines)

    @property
    def line(self) -> str:
        return self.lines[self.index]

    def advance(self, count: int = 1) -> None:
        self.index += count

    def get_reference(self, label: str) -> Reference | None:
        return self.references.get(label)
