from __future__ import annotations

import re
from collections.abc import Sequence
from typing import TYPE_CHECKING

from wenmode.nodes import Html
from wenmode.state import BlockState
from wenmode.utils import compile_disallowed_html_filter, filter_disallowed_html

from ..base import BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


BLOCK_TAGS = (
    'address',
    'article',
    'aside',
    'base',
    'basefont',
    'blockquote',
    'body',
    'caption',
    'center',
    'col',
    'colgroup',
    'dd',
    'details',
    'dialog',
    'dir',
    'div',
    'dl',
    'dt',
    'fieldset',
    'figcaption',
    'figure',
    'footer',
    'form',
    'frame',
    'frameset',
    'h1',
    'h2',
    'h3',
    'h4',
    'h5',
    'h6',
    'head',
    'header',
    'hr',
    'html',
    'iframe',
    'legend',
    'li',
    'link',
    'main',
    'menu',
    'menuitem',
    'nav',
    'noframes',
    'ol',
    'optgroup',
    'option',
    'p',
    'param',
    'search',
    'section',
    'summary',
    'table',
    'tbody',
    'td',
    'tfoot',
    'th',
    'thead',
    'title',
    'tr',
    'track',
    'ul',
)
BLOCK_TAGS_PATTERN = '|'.join(BLOCK_TAGS)
HTML_BLOCK_TAG_RE = re.compile(rf'(?i)^</?(?:{BLOCK_TAGS_PATTERN})(?:\s|/?>|$)')
HTML_SCRIPT_STYLE_RE = re.compile(r'(?i)^<(script|pre|style|textarea)(?:\s|>|$)')
HTML_OPEN_TAG_RE = re.compile(r'(?i)^<([A-Za-z][A-Za-z0-9-]*)')
HTML_DECLARATION_RE = re.compile(r'^<![A-Z]')
COMPLETE_HTML_TAG_RE = re.compile(
    r'(?i)</?[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*\s*/?>[ \t]*'
)


class HtmlBlock(BlockRule):
    def __init__(self, disallowed_tags: Sequence[str] = ()) -> None:
        super().__init__(
            'html_block',
            rf'(?i:[ \t]{{0,3}}<(?:script(?:\s|>|$)|pre(?:\s|>|$)|style(?:\s|>|$)|!--|\?|![A-Z]|\!\[CDATA\[|/?(?:{BLOCK_TAGS_PATTERN})(?:\s|/?>|$)|[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*\s*/?>[ \t]*$|/[A-Za-z][A-Za-z0-9-]*\s*>[ \t]*$))',
        )
        self.disallowed_html_filter = compile_disallowed_html_filter(disallowed_tags)

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Html:
        first = state.line
        stripped = first.rstrip('\r\n').lstrip(' \t')
        lines: list[str] = []

        end_pattern = html_end_pattern(stripped)
        if end_pattern is not None:
            while not state.done:
                lines.append(state.line)
                if end_pattern.search(state.line):
                    state.advance()
                    break
                state.advance()
            return self.html_node(''.join(lines))

        if is_html_block_tag(stripped) or is_complete_html_tag(stripped):
            while not state.done and state.line.strip() != '':
                lines.append(state.line)
                state.advance()
            return self.html_node(''.join(lines))

        state.advance()
        return self.html_node(first)

    def html_node(self, value: str) -> Html:
        filtered = filter_disallowed_html(value, self.disallowed_html_filter)
        data = {'escaped': True} if filtered != value else None
        return Html(value=filtered, data=data)


def html_end_pattern(line: str) -> re.Pattern[str] | None:
    if HTML_SCRIPT_STYLE_RE.match(line):
        tag = HTML_OPEN_TAG_RE.match(line)
        if tag is not None:
            return re.compile(rf'(?i)</{tag.group(1)}\s*>')
    if line.startswith('<!--'):
        return re.compile(r'-->')
    if line.startswith('<?'):
        return re.compile(r'\?>')
    if HTML_DECLARATION_RE.match(line):
        return re.compile(r'>')
    if line.startswith('<![CDATA['):
        return re.compile(r']]>')
    return None


def is_html_block_tag(line: str) -> bool:
    return HTML_BLOCK_TAG_RE.match(line) is not None


def is_complete_html_tag(line: str) -> bool:
    return COMPLETE_HTML_TAG_RE.fullmatch(line) is not None
