from __future__ import annotations

from wenmode.rules.base import Rule


class Paragraph(Rule):
    def __init__(self) -> None:
        super().__init__('paragraph')
