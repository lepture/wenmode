from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Callable, ClassVar

from wenmode.renderers.asciidoc import AsciiDocRenderContext, AsciiDocRenderer
from wenmode.renderers.base import RenderContext
from wenmode.renderers.markdown import MarkdownRenderer
from wenmode.renderers.rst import RSTRenderContext, RSTRenderer
from wenmode.rules import BlockCandidate, BlockRule, RootTransform, Rule

from .._parser.state import BlockState
from .._parser.store import StateKey
from .types import RendererHandlers

if TYPE_CHECKING:
    from wenmode import Wenmode
    from wenmode.nodes import Node, Root
    from wenmode.parser import Parser

FrontmatterLoad = Callable[[str], Any]
FrontmatterDump = Callable[[Any], str | None]
FRONTMATTER_FENCE_RE = re.compile(r'---[ \t]*(?:\r?\n)?$')
RST_FIELD_NAME_RE = re.compile(r'^[^\r\n:]+$')
MISSING = object()


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

    def __init__(self, load: FrontmatterLoad | None = None, data_key: str = 'frontmatter') -> None:
        super().__init__()
        self.load = load or load_simple_frontmatter
        self.root_transforms = [FrontmatterTransform(data_key)]

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Node | None:
        if state.depth != 0 or state.index != 0:
            return None

        closing_index = find_closing_fence(state, state.index + 1)
        if closing_index is None:
            return None

        body = ''.join(state.line_at(index) for index in range(state.index + 1, closing_index))
        frontmatter = state.store.get(FRONTMATTER_KEY)
        frontmatter.found = True
        frontmatter.value = self.load(body)
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


def load_simple_frontmatter(source: str) -> dict[str, str]:
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


def dump_simple_frontmatter(value: Any) -> str | None:
    if not isinstance(value, Mapping):
        return None

    lines: list[str] = []
    for key, item in value.items():
        name = str(key).strip()
        if not name:
            continue
        text = dump_simple_scalar(item)
        if text:
            lines.append(f'{name}: {text}')
        else:
            lines.append(f'{name}:')
    return '\n'.join(lines)


def dump_simple_scalar(value: Any) -> str:
    if value is None:
        return ''
    if isinstance(value, bool):
        return 'true' if value else 'false'
    return str(value).replace('\r', ' ').replace('\n', ' ').strip()


def unquote_scalar(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    return value


def root_frontmatter(root: Root, data_key: str) -> Any:
    if root.data is None or data_key not in root.data:
        return MISSING
    return root.data[data_key]


def render_markdown_frontmatter(value: Any, dump: FrontmatterDump) -> str:
    body = dump(value)
    if body is None:
        return ''
    body = body.rstrip('\n')
    if body:
        return f'---\n{body}\n---\n\n'
    return '---\n---\n\n'


def render_rst_frontmatter(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ''

    lines: list[str] = []
    for key, item in value.items():
        name = str(key).strip()
        if not name or RST_FIELD_NAME_RE.fullmatch(name) is None:
            continue
        text = dump_simple_scalar(item)
        if text:
            lines.append(f':{name}: {text}')
        else:
            lines.append(f':{name}:')
    if not lines:
        return ''
    return '\n'.join(lines) + '\n\n'


def render_asciidoc_frontmatter(value: Any) -> str:
    if not isinstance(value, Mapping):
        return ''

    lines: list[str] = []
    for key, item in value.items():
        name = str(key).strip()
        if not name or RST_FIELD_NAME_RE.fullmatch(name) is None:
            continue
        text = dump_simple_scalar(item)
        if text:
            lines.append(f':{name}: {text}')
        else:
            lines.append(f':{name}:')
    if not lines:
        return ''
    return '\n'.join(lines) + '\n\n'


def render_markdown_frontmatter_prelude(
    data_key: str, dump: FrontmatterDump
) -> Callable[[MarkdownRenderer, Root, RenderContext], str]:
    def render_frontmatter(renderer: MarkdownRenderer, node: Root, context: RenderContext) -> str:
        value = root_frontmatter(node, data_key)
        if value is MISSING:
            return ''
        return render_markdown_frontmatter(value, dump)

    return render_frontmatter


def render_rst_frontmatter_prelude(data_key: str) -> Callable[[RSTRenderer, Root, RSTRenderContext], str]:
    def render_frontmatter(renderer: RSTRenderer, node: Root, context: RSTRenderContext) -> str:
        value = root_frontmatter(node, data_key)
        if value is MISSING:
            return ''
        return render_rst_frontmatter(value)

    return render_frontmatter


def render_asciidoc_frontmatter_prelude(
    data_key: str,
) -> Callable[[AsciiDocRenderer, Root, AsciiDocRenderContext], str]:
    def render_frontmatter(renderer: AsciiDocRenderer, node: Root, context: AsciiDocRenderContext) -> str:
        value = root_frontmatter(node, data_key)
        if value is MISSING:
            return ''
        return render_asciidoc_frontmatter(value)

    return render_frontmatter


def create_handlers(data_key: str, dump: FrontmatterDump) -> RendererHandlers:
    return {
        'markdown': {'root:pre': render_markdown_frontmatter_prelude(data_key, dump)},
        'rst': {'root:pre': render_rst_frontmatter_prelude(data_key)},
        'asciidoc': {'root:pre': render_asciidoc_frontmatter_prelude(data_key)},
    }


nodes: dict[str, type[Node]] = {}
rules: list[type[Rule] | Rule] = [FrontmatterRule]


@dataclass(frozen=True)
class FrontmatterPlugin:
    load: FrontmatterLoad | None = None
    dump: FrontmatterDump | None = None
    data_key: str = 'frontmatter'

    def setup(self, wen: Wenmode, /) -> None:
        frontmatter_dump = self.dump or dump_simple_frontmatter
        wen.register_rule(FrontmatterRule(load=self.load or load_simple_frontmatter, data_key=self.data_key))
        wen.register_renderer_handlers(create_handlers(self.data_key, frontmatter_dump))


def configure(
    *, load: FrontmatterLoad | None = None, dump: FrontmatterDump | None = None, data_key: str = 'frontmatter'
) -> FrontmatterPlugin:
    return FrontmatterPlugin(load=load, dump=dump, data_key=data_key)


def setup(wen: Wenmode, /) -> None:
    configure().setup(wen)
