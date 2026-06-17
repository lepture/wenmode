from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING
from urllib.parse import quote

from wenmode.nodes import Html, Link, Node, Text
from wenmode.state import BlockState
from wenmode.utils import compile_disallowed_html_filter, filter_disallowed_html

from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


URI_RE = r'<(?P<uri>[A-Za-z][A-Za-z0-9.+-]{1,31}:[^<>\s]*)>'
EMAIL_RE = r'<(?P<email>[A-Za-z0-9.!#$%&\'*+/=?^_`{|}~-]+@[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*)>'
HTML_OPEN_TAG_RE = (
    r'<[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*\s*/?>'
)
HTML_CLOSE_TAG_RE = r'</[A-Za-z][A-Za-z0-9-]*\s*>'
HTML_TAG_RE = rf'(?:{HTML_OPEN_TAG_RE}|{HTML_CLOSE_TAG_RE})'
HTML_RE = rf'<!--(?!>|->)[\s\S]*?-->|<!---?>|<\?.*?\?>|<![A-Z]+[^>]*>|<!\[CDATA\[.*?\]\]>|{HTML_TAG_RE}'


class Autolink(InlineRule):
    def __init__(self) -> None:
        super().__init__('autolink', rf'{URI_RE}|{EMAIL_RE}', '<')

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        uri = match.groupdict().get('uri')
        if uri is not None:
            return Link(url=normalize_uri(uri), children=[Text(value=uri)]), match.end()

        email = match.group('email')
        return Link(url='mailto:' + normalize_uri(email), children=[Text(value=email)]), match.end()


class RawHtml(InlineRule):
    def __init__(self, disallowed_tags: Sequence[str] = ()) -> None:
        super().__init__('raw_html', HTML_RE, '<')
        self.disallowed_html_filter = compile_disallowed_html_filter(disallowed_tags)

    def parse(
        self, parser: Parser, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        value = match.group(0)
        filtered = filter_disallowed_html(value, self.disallowed_html_filter)
        data = {'escaped': True} if filtered != value else None
        return Html(value=filtered, data=data), match.end()


def normalize_uri(value: str) -> str:
    return quote(value, safe="/:?#@!$&'()*+,;=%._~-")
