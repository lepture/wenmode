from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Link, Node, Text
from wenmode.state import BlockState

from ..base import InlineRule
from .html import normalize_uri

if TYPE_CHECKING:
    from wenmode.parser import Parser


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
URL_PREFIXES = ('http://', 'https://', 'mailto:', 'xmpp:', 'www.')
EMAIL_LOCAL_CHARS = frozenset("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789.!#$%&'*+/=?^_`{|}~-")
EMAIL_RE = re.compile(
    r"(?i)[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)+"
)


class ExtendedAutolink(InlineRule):
    def __init__(self) -> None:
        super().__init__('extended_autolink', EXTENDED_AUTOLINK_RE)

    def search(self, text: str, pos: int = 0) -> re.Match[str] | None:
        url_match = self.search_url(text, pos)
        email_match = self.search_email(text, pos)
        if email_match is None:
            return url_match
        if url_match is None or email_match.start() < url_match.start():
            return email_match
        return url_match

    def search_url(self, text: str, pos: int) -> re.Match[str] | None:
        lower_text = text.lower()
        start = find_url_prefix(lower_text, pos)
        while start is not None:
            match = self.compiled.match(text, start) if is_autolink_boundary(text, start) else None
            if match is not None:
                return match
            start = find_url_prefix(lower_text, start + 1)
        return None

    def search_email(self, text: str, pos: int) -> re.Match[str] | None:
        cursor = text.find('@', pos)
        while cursor != -1:
            start = email_start(text, cursor)
            if start >= pos and is_email_boundary(text, start):
                match = self.compiled.match(text, start)
                if match is not None:
                    return match
            cursor = text.find('@', cursor + 1)
        return None

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
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
    return EMAIL_RE.fullmatch(value) is not None


def email_start(text: str, at: int) -> int:
    start = at
    while start > 0 and text[start - 1] in EMAIL_LOCAL_CHARS:
        start -= 1
    return start


def is_email_boundary(text: str, start: int) -> bool:
    return is_autolink_boundary(text, start)


def is_autolink_boundary(text: str, start: int) -> bool:
    return start == 0 or not (text[start - 1].isalnum() or text[start - 1] == '@')


def find_url_prefix(lower_text: str, pos: int) -> int | None:
    found = -1
    for prefix in URL_PREFIXES:
        index = lower_text.find(prefix, pos)
        if index != -1 and (found == -1 or index < found):
            found = index
    return None if found == -1 else found
