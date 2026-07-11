from __future__ import annotations

import re
from collections.abc import Sequence


def compile_disallowed_html_filter(tags: Sequence[str]) -> re.Pattern[str] | None:
    if not tags:
        return None
    tag_pattern = '|'.join(re.escape(tag) for tag in tags)
    return re.compile(rf'(?i)<(?=/?(?:{tag_pattern})(?:\s|/?>|$))')


def filter_disallowed_html(value: str, pattern: re.Pattern[str] | None) -> str:
    if pattern is None:
        return value
    return pattern.sub('&lt;', value)
