from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from wenmode.rules.base import BlockRule, Rule
from wenmode.rules.transforms import RootTransform
from wenmode.state import BlockState, StateKey

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.nodes import Node, Root
    from wenmode.parser import Parser

FrontmatterParser = Callable[[str], Any]
FRONTMATTER_FENCE_RE = re.compile(r'---[ \t]*(?:\r?\n)?$')


@dataclass
class FrontmatterState:
    found: bool = False
    value: Any = None


FRONTMATTER_KEY = StateKey('wenmode.frontmatter', FrontmatterState)


class FrontmatterRule(BlockRule):
    """Parse top-level ``---`` front matter without emitting a block node."""

    order: ClassVar[int] = 0
    name = 'frontmatter'
    pattern = r'---[ \t]*(?:\r?\n)?$'

    def __init__(
        self,
        parser: FrontmatterParser | None = None,
        data_key: str = 'frontmatter',
    ) -> None:
        super().__init__()
        self.parser = parser or parse_simple_frontmatter
        self.root_transforms = [FrontmatterTransform(data_key)]

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        if state.depth != 0 or state.index != 0:
            return None

        closing_index = find_closing_fence(state, state.index + 1)
        if closing_index is None:
            return None

        body = ''.join(state.line_at(index) for index in range(state.index + 1, closing_index))
        frontmatter = state.store.get(FRONTMATTER_KEY)
        frontmatter.found = True
        frontmatter.value = self.parser(body)
        state.index = closing_index + 1
        return None


class FrontmatterTransform(RootTransform):
    def __init__(self, data_key: str = 'frontmatter') -> None:
        self.name = f'frontmatter:{data_key}'
        self.data_key = data_key

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        frontmatter = state.store.get(FRONTMATTER_KEY)
        if not frontmatter.found:
            return
        if root.data is None:
            root.data = {}
        root.data[self.data_key] = frontmatter.value


def find_closing_fence(state: BlockState, start_index: int) -> int | None:
    index = start_index
    while state.has_index(index):
        if FRONTMATTER_FENCE_RE.fullmatch(state.line_at(index)):
            return index
        index += 1
    return None


def parse_simple_frontmatter(source: str) -> dict[str, str]:
    data: dict[str, str] = {}
    for line in source.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or ':' not in stripped:
            continue
        key, value = stripped.split(':', 1)
        key = key.strip()
        if key:
            data[key] = unquote_scalar(value.strip())
    return data


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


rules: list[type[Rule] | Rule] = [FrontmatterRule]


def setup(
    wenmode: Wenmode,
    parser: FrontmatterParser | None = None,
    data_key: str = 'frontmatter',
    **options: Any,
) -> None:
    wenmode.register_rule(FrontmatterRule(parser=parser or parse_simple_frontmatter, data_key=data_key))
