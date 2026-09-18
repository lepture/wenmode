from __future__ import annotations

import re
import string
from collections.abc import Set
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import TYPE_CHECKING, cast

from ._parser.store import StateKey
from ._parser.transforms import NODE_TRANSFORM_FINALIZATION, NodeTransform
from .ast import find_all, plain_text, walk
from .nodes import ContainerDirective, Heading, Html, LeafDirective, LiteralDirective, Node, Root, TextDirective

if TYPE_CHECKING:
    from ._parser.state import BlockState
    from .parser import Parser

SLUG_PUNCTUATION = ''.join(char for char in string.punctuation if char not in '-_')
SLUG_PUNCTUATION_RE = re.compile('[' + re.escape(SLUG_PUNCTUATION) + ']')
SLUG_SPACE_RE = re.compile(r'\s+')
HEADING_SLUGGERS = StateKey[dict[str, 'Slugger']]('wenmode.heading.sluggers', lambda: {})
GENERATED_HEADING_IDS = StateKey[dict[str, list['_GeneratedHeadingId']]]('wenmode.heading.generated_ids', lambda: {})


@dataclass
class _GeneratedHeadingId:
    heading: Heading
    identifier: str


class Slugger:
    """Generate unique slug IDs for headings."""

    name = 'default'

    def __init__(self) -> None:
        self.seen: dict[str, int] = {}
        self.used: set[str] = set()

    def slug(self, value: str) -> str:
        """Return a unique slug for a heading title."""
        base = slugify(value)
        index = self.seen.get(base, 0)
        slug = base if index == 0 else f'{base}-{index}'
        while slug in self.used:
            index += 1
            slug = f'{base}-{index}'
        self.seen[base] = index + 1
        self.used.add(slug)
        return slug

    def use(self, value: str) -> None:
        """Mark an existing slug as already used."""
        self.seen[value] = max(1, self.seen.get(value, 0))
        self.used.add(value)


class HeadingIdTransform(NodeTransform):
    """Node transform that adds generated IDs to heading nodes.

    :param slugger_factory: Slugger class used to generate heading IDs.
    """

    defer_inlines = True

    def __init__(self, slugger_factory: type[Slugger] = Slugger) -> None:
        self.slugger_factory = slugger_factory
        self.name = f'heading_id:{slugger_factory.name}'

    def transform(self, parser: Parser, node: Node, state: BlockState) -> None:
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
            return

        if heading.data is None:
            heading.data = {}
        identifier = slugger.slug(plain_text(heading.children))
        heading.data['id'] = identifier
        if state.store.get(NODE_TRANSFORM_FINALIZATION):
            state.store.get(GENERATED_HEADING_IDS).setdefault(self.name, []).append(
                _GeneratedHeadingId(heading, identifier)
            )

    def finalize(self, parser: Parser, root: Root, state: BlockState) -> None:
        generated = state.store.get(GENERATED_HEADING_IDS)
        records = generated.get(self.name, [])
        if not records:
            return
        generated_nodes = {
            id(record.heading)
            for group in generated.values()
            for record in group
            if record.heading.data and record.heading.data.get('id') == record.identifier
        }
        explicit_ids = _collect_document_ids(root, exclude_heading_ids=generated_nodes)
        if not any(record.identifier in explicit_ids for record in records):
            return
        occupied = _collect_document_ids(root)
        slugger = state.store.get(HEADING_SLUGGERS)[self.name]
        for identifier in explicit_ids:
            slugger.use(identifier)
        suffixes: dict[str, int] = {}
        for record in records:
            if not record.heading.data or record.heading.data.get('id') != record.identifier:
                continue
            if record.identifier in explicit_ids:
                identifier = _unique_heading_id(plain_text(record.heading.children), slugger, occupied, suffixes)
                record.heading.data['id'] = identifier
                record.identifier = identifier
                occupied.add(identifier)


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
    headings = iter_headings(node)
    replaced = {id(heading) for heading in headings if overwrite and min_depth <= heading.depth <= max_depth}
    occupied = _collect_document_ids(node, exclude_heading_ids=replaced)
    for identifier in occupied:
        slugger.use(identifier)
    suffixes: dict[str, int] = {}
    for heading in headings:
        if not (min_depth <= heading.depth <= max_depth):
            continue
        if heading.data:
            current_id = heading.data.get('id')
        else:
            current_id = None
        if isinstance(current_id, str) and not overwrite:
            continue
        if heading.data is None:
            heading.data = {}
        identifier = _unique_heading_id(plain_text(heading.children), slugger, occupied, suffixes)
        heading.data['id'] = identifier
        occupied.add(identifier)


def _unique_heading_id(value: str, slugger: Slugger, occupied: set[str], suffixes: dict[str, int]) -> str:
    attempted: set[str] = set()
    identifier = slugger.slug(value)
    while identifier in occupied and identifier not in attempted:
        attempted.add(identifier)
        identifier = slugger.slug(value)
    if identifier not in occupied:
        return identifier

    # Custom sluggers may return a constant ID. Do not loop indefinitely when
    # asking them for a replacement; retain their format and add a unique suffix.
    base = identifier
    index = suffixes.get(base, 1)
    while f'{base}-{index}' in occupied:
        index += 1
    suffixes[base] = index + 1
    return f'{base}-{index}'


class _HtmlIdCollector(HTMLParser):
    def __init__(self, identifiers: set[str]) -> None:
        super().__init__()
        self.identifiers = identifiers

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for name, value in attrs:
            if name == 'id' and value is not None:
                self.identifiers.add(value)

    def parse_html_declaration(self, index: int) -> int:
        try:
            return super().parse_html_declaration(index)
        except AssertionError:
            # HTMLParser rejects unknown marked-section declarations, whereas
            # raw Markdown HTML is permissive. Skip them and keep collecting IDs.
            end = self.rawdata.find('>', index + 2)
            return end + 1 if end >= 0 else -1


def _collect_document_ids(node: Node, *, exclude_heading_ids: Set[int] = frozenset()) -> set[str]:
    identifiers: set[str] = set()
    roots = [node]
    if isinstance(node, Root) and node.footnote_definitions:
        roots.extend(node.footnote_definitions.values())
    for root in roots:
        for descendant in walk(root):
            if descendant.data and id(descendant) not in exclude_heading_ids:
                identifier = descendant.data.get('id')
                if isinstance(identifier, str):
                    identifiers.add(identifier)
            if isinstance(descendant, (ContainerDirective, LeafDirective, LiteralDirective, TextDirective)):
                if descendant.attributes and 'id' in descendant.attributes:
                    identifiers.add(descendant.attributes['id'])
            elif isinstance(descendant, Html) and not (descendant.data and descendant.data.get('escaped')):
                # Parse each fragment independently, so incomplete markup cannot
                # accumulate and repeatedly copy an ever-growing parser buffer.
                collector = _HtmlIdCollector(identifiers)
                collector.feed(descendant.value)
    return identifiers


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
