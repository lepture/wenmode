from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Literal
from urllib.parse import quote

from wenmode.nodes import Html, Link, Node, Text
from wenmode.utils import compile_disallowed_html_filter, filter_disallowed_html

from ..._parser.rule_base import InlineCandidate, InlineRule
from ..._parser.state import BlockState
from ..._parser.store import StateKey

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
GFM_HTML_COMMENT_RE = r'<!--(?!>|->)(?:(?!--)[\s\S])*?-->'
HTML_COMMENT_RE = GFM_HTML_COMMENT_RE
HTML_RE = rf'{HTML_COMMENT_RE}|<\?[\s\S]*?\?>|<![A-Za-z][^>]*>|<!\[CDATA\[[\s\S]*?\]\]>|{HTML_TAG_RE}'
HTML_COMMENT_STYLE_RE = {'commonmark': COMMONMARK_HTML_COMMENT_RE, 'gfm': GFM_HTML_COMMENT_RE}


HTML_END_FAILURES = StateKey[dict[tuple[int, str], tuple[str, int]]]('wenmode.html.ending_failures', lambda: {})
HTML_TAG_PATTERN = re.compile(HTML_TAG_RE)


def html_span_end(text: str, start: int, state: BlockState, comment_style: str = 'commonmark') -> int | None:
    """Dispatch literal-ended HTML before attempting ordinary tag grammar."""
    if text.startswith('<!--', start):
        if comment_style == 'commonmark' and text.startswith(('<!-->', '<!--->'), start):
            return start + (5 if text.startswith('<!-->', start) else 6)
        content_start, ending = start + 4, '-->'
        if comment_style == 'gfm':
            if text.startswith(('>', '->'), content_start):
                return None
            ending = '--'
    elif text.startswith('<?', start):
        content_start, ending = start + 2, '?>'
    elif text.startswith('<![CDATA[', start):
        content_start, ending = start + 9, ']]>'
    elif (
        text.startswith('<!', start)
        and start + 2 < len(text)
        and text[start + 2] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    ):
        content_start, ending = start + 3, '>'
    else:
        match = HTML_TAG_PATTERN.match(text, start)
        return match.end() if match is not None else None
    failures = state.store.get(HTML_END_FAILURES)
    key = (id(text), ending)
    cached = failures.get(key)
    if cached is not None and cached[0] is text and content_start >= cached[1]:
        return None
    close = text.find(ending, content_start)
    if close == -1:
        failures[key] = (text, content_start)
        return None
    if ending == '--':
        return close + 3 if text.startswith('-->', close) else None
    return close + len(ending)


class Autolink(InlineRule):
    """Parse angle-bracket URI and email autolinks.

    Markdown syntax:

    .. code-block:: markdown

       <https://example.com>
    """

    name = 'autolink'
    pattern = rf'{URI_RE}|{EMAIL_RE}'
    opener = '<'

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        match = candidate.match
        assert match is not None
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
    opener = '<'

    def __init__(
        self, disallowed_tags: Sequence[str] = (), comment_style: Literal['commonmark', 'gfm'] = 'commonmark'
    ) -> None:
        comment_re = HTML_COMMENT_STYLE_RE[comment_style]
        html_re = rf'{comment_re}|<\?[\s\S]*?\?>|<![A-Za-z][^>]*>|<!\[CDATA\[[\s\S]*?\]\]>|{HTML_TAG_RE}'
        super().__init__(pattern=html_re)
        self.disallowed_html_filter = compile_disallowed_html_filter(disallowed_tags)
        self.comment_style = comment_style

    def match_candidate(self, text: str, start: int) -> InlineCandidate | None:
        if text.startswith(('<!--', '<?', '<![CDATA['), start) or (
            text.startswith('<!', start)
            and start + 2 < len(text)
            and text[start + 2] in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
        ):
            return InlineCandidate(start)
        return super().match_candidate(text, start)

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        match = candidate.match
        end = match.end() if match is not None else html_span_end(text, candidate.start, state, self.comment_style)
        if end is None:
            return None, candidate.start
        value = text[candidate.start : end]
        filtered = filter_disallowed_html(value, self.disallowed_html_filter)
        if filtered != value:
            data = {'escaped': True}
        else:
            data = None
        return Html(value=filtered, data=data), end


def normalize_uri(value: str) -> str:
    return quote(value, safe="/:?#@!$&'()*+,;=%._~-")
