from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from wenmode.nodes import Node


@dataclass
class Reference:
    url: str
    title: str | None = None


@dataclass
class Footnote:
    identifier: str
    label: str
    children: list[Node]


@dataclass
class BlockState:
    lines: list[str]
    index: int = 0
    references: dict[str, Reference] = field(default_factory=dict)
    footnotes: dict[str, Footnote] = field(default_factory=dict)
    depth: int = 0
    pending_inlines: list[tuple[list[Node], str]] = field(default_factory=list)
    pending_inline_callbacks: list[Callable[[], None]] = field(default_factory=list)
    defer_inlines: bool = False

    @classmethod
    def from_text(
        cls,
        text: str,
        references: dict[str, Reference] | None = None,
        footnotes: dict[str, Footnote] | None = None,
        depth: int = 0,
        pending_inlines: list[tuple[list[Node], str]] | None = None,
        pending_inline_callbacks: list[Callable[[], None]] | None = None,
        defer_inlines: bool = False,
    ) -> BlockState:
        return cls(
            text.splitlines(keepends=True),
            references=references if references is not None else {},
            footnotes=footnotes if footnotes is not None else {},
            depth=depth,
            pending_inlines=pending_inlines if pending_inlines is not None else [],
            pending_inline_callbacks=pending_inline_callbacks if pending_inline_callbacks is not None else [],
            defer_inlines=defer_inlines,
        )

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

    def get_footnote(self, identifier: str) -> Footnote | None:
        return self.footnotes.get(identifier)
