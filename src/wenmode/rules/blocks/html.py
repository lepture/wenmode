from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Html
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


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


class HtmlBlock(BlockRule):
    def __init__(self) -> None:
        tags = '|'.join(BLOCK_TAGS)
        super().__init__(
            'html_block',
            rf'(?i:[ \t]{{0,3}}<(?:script(?:\s|>|$)|pre(?:\s|>|$)|style(?:\s|>|$)|!--|\?|![A-Z]|\!\[CDATA\[|/?(?:{tags})(?:\s|/?>|$)|[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*\s*/?>[ \t]*$|/[A-Za-z][A-Za-z0-9-]*\s*>[ \t]*$))',
        )

    def parse(self, parser: Wenmode, state: BlockState, match: re.Match[str]) -> Html:
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
            return Html(value=''.join(lines))

        if is_html_block_tag(stripped) or is_complete_html_tag(stripped):
            while not state.done and state.line.strip() != '':
                lines.append(state.line)
                state.advance()
            return Html(value=''.join(lines))

        state.advance()
        return Html(value=first)


def html_end_pattern(line: str) -> re.Pattern[str] | None:
    if re.match(r'(?i)^<(script|pre|style|textarea)(?:\s|>|$)', line):
        tag = re.match(r'(?i)^<([A-Za-z][A-Za-z0-9-]*)', line)
        if tag is not None:
            return re.compile(rf'(?i)</{tag.group(1)}\s*>')
    if line.startswith('<!--'):
        return re.compile(r'-->')
    if line.startswith('<?'):
        return re.compile(r'\?>')
    if re.match(r'^<![A-Z]', line):
        return re.compile(r'>')
    if line.startswith('<![CDATA['):
        return re.compile(r']]>')
    return None


def is_html_block_tag(line: str) -> bool:
    tags = '|'.join(BLOCK_TAGS)
    return re.match(rf'(?i)^</?(?:{tags})(?:\s|/?>|$)', line) is not None


def is_complete_html_tag(line: str) -> bool:
    return (
        re.fullmatch(
            r'(?i)</?[A-Za-z][A-Za-z0-9-]*(?:\s+[A-Za-z_:][A-Za-z0-9_.:-]*(?:\s*=\s*(?:[^\s"\'=<>`]+|\'[^\']*\'|"[^"]*"))?)*\s*/?>[ \t]*',
            line,
        )
        is not None
    )
