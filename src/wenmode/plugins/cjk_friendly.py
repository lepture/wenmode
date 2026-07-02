from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wenmode.rules.inlines.emphasis import Emphasis
from wenmode.rules.inlines.extended_autolink import ExtendedAutolink

if TYPE_CHECKING:
    from wenmode import Wenmode


def setup(wen: Wenmode, **options: Any) -> None:
    wen.register_rule(Emphasis(cjk_friendly=True))
    if 'extended_autolink' in wen.parser.rules:
        wen.register_rule(ExtendedAutolink(cjk_friendly=True))
