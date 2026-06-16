from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Link, Node, Text
from wenmode.rules.base import InlineRule
from wenmode.rules.inlines.html import normalize_uri
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


EXTENDED_AUTOLINK_RE = (
    r'(?i)(?<![A-Za-z0-9@])(?:'
    r'(?:https?://|mailto:|xmpp:)[^\s<]+'
    r'|www\.[^\s<]+'
    r'|[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9]'
    r'(?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?'
    r'(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+'
    r')'
)
TRAILING_PUNCTUATION = '?!.,:*_~'


class ExtendedAutolink(InlineRule):
    def __init__(self) -> None:
        super().__init__('extended_autolink', EXTENDED_AUTOLINK_RE)

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        value = match.group(0)
        value = trim_trailing_punctuation(value)
        if not value:
            return None, match.start()

        url = value
        if value.lower().startswith('www.'):
            url = 'http://' + value
        elif is_email(value):
            url = 'mailto:' + value

        return Link(url=normalize_uri(url), children=[Text(value=value)]), match.start() + len(value)


def trim_trailing_punctuation(value: str) -> str:
    while value and value[-1] in TRAILING_PUNCTUATION:
        value = value[:-1]

    while value.endswith(')') and value.count(')') > value.count('('):
        value = value[:-1]

    return value


def is_email(value: str) -> bool:
    return re.fullmatch(
        r"(?i)[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+",
        value,
    ) is not None
