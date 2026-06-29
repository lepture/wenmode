from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wenmode.rules.inlines.emphasis import Emphasis
from wenmode.rules.inlines.extended_autolink import ExtendedAutolink

if TYPE_CHECKING:
    from wenmode import Wenmode


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rule(Emphasis(cjk_friendly=True))
    if 'extended_autolink' in wenmode.parser.rules:
        wenmode.register_rule(ExtendedAutolink(cjk_friendly=True))
