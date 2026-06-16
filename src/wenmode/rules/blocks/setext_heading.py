from __future__ import annotations

from wenmode.rules.base import Rule


class SetextHeading(Rule):
    def __init__(self) -> None:
        super().__init__('setext_heading')
