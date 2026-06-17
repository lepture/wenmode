from __future__ import annotations

import re
import string

from .nodes import Heading, Image, Literal, Node, Parent

SLUG_PUNCTUATION = ''.join(char for char in string.punctuation if char not in '-_')
SLUG_PUNCTUATION_RE = re.compile('[' + re.escape(SLUG_PUNCTUATION) + ']')
SLUG_SPACE_RE = re.compile(r'\s+')


class Slugger:
    name = 'default'

    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def slug(self, value: str) -> str:
        base = slugify(value)
        index = self.seen.get(base, 0)
        self.seen[base] = index + 1
        if index == 0:
            return base
        return f'{base}-{index}'

    def use(self, value: str) -> None:
        self.seen[value] = self.seen.get(value, 0) + 1


def add_heading_ids(
    node: Node,
    *,
    slugger: Slugger | None = None,
    min_depth: int = 1,
    max_depth: int = 6,
    overwrite: bool = False,
) -> None:
    slugger = slugger or Slugger()
    for heading in iter_headings(node):
        if not (min_depth <= heading.depth <= max_depth):
            continue
        current_id = heading.data.get('id') if heading.data else None
        if isinstance(current_id, str) and not overwrite:
            slugger.use(current_id)
            continue
        if heading.data is None:
            heading.data = {}
        heading.data['id'] = slugger.slug(plain_text(heading.children))


def iter_headings(node: Node) -> list[Heading]:
    headings: list[Heading] = []
    collect_headings(node, headings)
    return headings


def collect_headings(node: Node, headings: list[Heading]) -> None:
    if isinstance(node, Heading):
        headings.append(node)
    children = getattr(node, 'children', None)
    if isinstance(children, list):
        for child in children:
            collect_headings(child, headings)


def plain_text(nodes: list[Node]) -> str:
    return ''.join(plain_text_node(node) for node in nodes)


def plain_text_node(node: Node) -> str:
    if isinstance(node, Image):
        return node.alt
    if isinstance(node, Literal):
        return node.value
    if isinstance(node, Parent):
        return plain_text(node.children)
    label = getattr(node, 'label', None)
    if isinstance(label, str):
        return label
    identifier = getattr(node, 'identifier', None)
    if isinstance(identifier, str):
        return identifier
    return ''


def slugify(value: str) -> str:
    slug = value.strip().lower()
    slug = SLUG_PUNCTUATION_RE.sub('', slug)
    slug = SLUG_SPACE_RE.sub('-', slug)
    slug = slug.strip('-')
    return slug or 'section'
