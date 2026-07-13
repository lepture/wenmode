from __future__ import annotations

import re
import string
from typing import TYPE_CHECKING, cast

from ._parser.store import StateKey
from .ast import find_all, plain_text
from .nodes import Heading, Node
from .rules.transforms import NodeTransform

if TYPE_CHECKING:
    from ._parser.state import BlockState
    from .parser import Parser

SLUG_PUNCTUATION = ''.join(char for char in string.punctuation if char not in '-_')
SLUG_PUNCTUATION_RE = re.compile('[' + re.escape(SLUG_PUNCTUATION) + ']')
SLUG_SPACE_RE = re.compile(r'\s+')
HEADING_SLUGGERS = StateKey[dict[str, 'Slugger']]('wenmode.heading.sluggers', lambda: {})


class Slugger:
    """Generate unique slug IDs for headings."""

    name = 'default'

    def __init__(self) -> None:
        self.seen: dict[str, int] = {}

    def slug(self, value: str) -> str:
        """Return a unique slug for a heading title."""
        base = slugify(value)
        index = self.seen.get(base, 0)
        self.seen[base] = index + 1
        if index == 0:
            return base
        return f'{base}-{index}'

    def use(self, value: str) -> None:
        """Mark an existing slug as already used."""
        self.seen[value] = self.seen.get(value, 0) + 1


class HeadingIdTransform(NodeTransform):
    """Node transform that adds generated IDs to heading nodes.

    :param slugger_factory: Slugger class used to generate heading IDs.
    """

    defer_inlines = True

    def __init__(self, slugger_factory: type[Slugger] = Slugger) -> None:
        self.slugger_factory = slugger_factory
        self.name = f'heading_id:{slugger_factory.name}'

    def transform(self, parser: Parser, node: Node, state: BlockState) -> Node:
        heading = cast(Heading, node)
        sluggers = state.store.get(HEADING_SLUGGERS)
        slugger = sluggers.get(self.name)
        if slugger is None:
            slugger = self.slugger_factory()
            sluggers[self.name] = slugger

        if heading.data:
            current_id = heading.data.get('id')
        else:
            current_id = None
        if isinstance(current_id, str):
            slugger.use(current_id)
            return heading

        if heading.data is None:
            heading.data = {}
        heading.data['id'] = slugger.slug(plain_text(heading.children))
        return heading


def add_heading_ids(
    node: Node, *, slugger: Slugger, min_depth: int = 1, max_depth: int = 6, overwrite: bool = False
) -> None:
    """Add generated IDs to heading nodes in a tree.

    Existing heading IDs are preserved unless ``overwrite`` is ``True``.

    :param node: Root or subtree to update.
    :param slugger: Slug generator used to create unique IDs.
    :param min_depth: Minimum heading depth to update.
    :param max_depth: Maximum heading depth to update.
    :param overwrite: Whether to replace existing heading IDs.
    """
    for heading in iter_headings(node):
        if not (min_depth <= heading.depth <= max_depth):
            continue
        if heading.data:
            current_id = heading.data.get('id')
        else:
            current_id = None
        if isinstance(current_id, str) and not overwrite:
            slugger.use(current_id)
            continue
        if heading.data is None:
            heading.data = {}
        heading.data['id'] = slugger.slug(plain_text(heading.children))


def iter_headings(node: Node) -> list[Heading]:
    """Return all heading nodes under a node."""
    return [cast(Heading, heading) for heading in find_all(node, Heading)]


def slugify(value: str) -> str:
    """Convert text into a URL-friendly slug."""
    slug = value.strip().lower()
    slug = SLUG_PUNCTUATION_RE.sub('', slug)
    slug = SLUG_SPACE_RE.sub('-', slug)
    slug = slug.strip('-')
    return slug or 'section'
