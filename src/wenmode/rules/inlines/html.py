from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

from wenmode.nodes import Html, Link, Node, Text
from wenmode.utils import compile_disallowed_html_filter, filter_disallowed_html

from ..._parser.state import BlockState
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
COMMONMARK_HTML_COMMENT_RE = r'<!-->|<!--->|<!--[\s\S]*?-->'
GFM_HTML_COMMENT_RE = r'<!--(?!>|->)(?:(?!--)[\s\S])*?(?<!-)-->'
HTML_COMMENT_RE = GFM_HTML_COMMENT_RE
HTML_RE = rf'{HTML_COMMENT_RE}|<\?.*?\?>|<![A-Z]+[^>]*>|<!\[CDATA\[.*?\]\]>|{HTML_TAG_RE}'
HTML_COMMENT_STYLE_RE = {
    'commonmark': COMMONMARK_HTML_COMMENT_RE,
    'gfm': GFM_HTML_COMMENT_RE,
}


class Autolink(InlineRule):
    """Parse angle-bracket URI and email autolinks.

    Markdown syntax:

    .. code-block:: markdown

       <https://example.com>
    """

    name = 'autolink'
    pattern = rf'{URI_RE}|{EMAIL_RE}'
    trigger_chars = '<'

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        uri = match.groupdict().get('uri')
        if uri is not None:
            text_node = Text(value=uri)
            source = parser.inline_source(text, state, match.start('uri'), match.end('uri'))
            if source is not None:
                text_node.position = source.position(0, len(uri))
            return Link(url=normalize_uri(uri), children=[text_node]), match.end()

        email = match.group('email')
        text_node = Text(value=email)
        source = parser.inline_source(text, state, match.start('email'), match.end('email'))
        if source is not None:
            text_node.position = source.position(0, len(email))
        return Link(url='mailto:' + normalize_uri(email), children=[text_node]), match.end()


class RawHtml(InlineRule):
    """Parse inline raw HTML.

    Markdown syntax:

    .. code-block:: markdown

       <span>HTML</span>

    :param disallowed_tags: HTML tag names that should be escaped during
        parsing.
    :param comment_style: ``"commonmark"`` uses CommonMark 0.31-style inline
        comments. ``"gfm"`` uses the stricter GFM 0.29 comment grammar.
    """

    name = 'raw_html'
    trigger_chars = '<'

    def __init__(
        self,
        disallowed_tags: Sequence[str] = (),
        comment_style: Literal['commonmark', 'gfm'] = 'commonmark',
    ) -> None:
        comment_re = HTML_COMMENT_STYLE_RE[comment_style]
        html_re = rf'{comment_re}|<\?.*?\?>|<![A-Z]+[^>]*>|<!\[CDATA\[.*?\]\]>|{HTML_TAG_RE}'
        super().__init__(pattern=html_re)
        self.disallowed_html_filter = compile_disallowed_html_filter(disallowed_tags)
        self.comment_style = comment_style

    def parse(self, parser: Parser, text: str, match: re.Match[str], state: BlockState) -> tuple[Node | None, int]:
        value = match.group(0)
        filtered = filter_disallowed_html(value, self.disallowed_html_filter)
        if filtered != value:
            data = {'escaped': True}
        else:
            data = None
        return Html(value=filtered, data=data), match.end()


def normalize_uri(value: str) -> str:
    return quote(value, safe="/:?#@!$&'()*+,;=%._~-")
