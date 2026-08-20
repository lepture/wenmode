from __future__ import annotations

import re
from collections.abc import Sequence

BLOCK_TAGS = frozenset({
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
})
VOID_TAGS = frozenset({
    'area',
    'base',
    'br',
    'col',
    'embed',
    'hr',
    'img',
    'input',
    'link',
    'meta',
    'param',
    'source',
    'track',
    'wbr',
})
HTML_BLOCK_TAG_RE = re.compile(rf'^</?(?:{"|".join(BLOCK_TAGS)})(?:\s|/?>|$)', re.I)
HTML_PRE_TAG_START_RE = re.compile(r'^<(script|pre|style|textarea)(?:\s|>|$)', re.I)


def compile_disallowed_html_filter(tags: Sequence[str]) -> re.Pattern[str] | None:
    if not tags:
        return None
    tag_pattern = '|'.join(re.escape(tag) for tag in tags)
    return re.compile(rf'<(?=/?(?:{tag_pattern})(?:\s|/?>|$))', re.I)


def filter_disallowed_html(value: str, pattern: re.Pattern[str] | None) -> str:
    if pattern is None:
        return value
    return pattern.sub('&lt;', value)


def is_html_block_tag(line: str) -> bool:
    return HTML_BLOCK_TAG_RE.match(line) is not None


def startswith_html_pre_tag(line: str) -> bool:
    return HTML_PRE_TAG_START_RE.match(line) is not None
