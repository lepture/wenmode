from __future__ import annotations

import bisect
from collections.abc import Sequence
from dataclasses import MISSING, dataclass, field, fields
from typing import Any
from typing import Literal as TypingLiteral


@dataclass(frozen=True, slots=True)
class Point:
    """A 1-based source point in the parsed Markdown document."""

    line: int
    column: int
    offset: int

    def to_ast(self) -> dict[str, int]:
        return {
            'line': self.line,
            'column': self.column,
            'offset': self.offset,
        }


@dataclass(frozen=True, slots=True)
class Position:
    """0-based source offset range for a node.

    ``Root.to_ast()`` converts these offsets to ``line`` and ``column`` fields
    when the root was produced by a position-aware parser. Calling
    ``Node.to_ast()`` on a standalone node emits offset-only positions.
    """

    start: int
    end: int

    def to_ast(self, line_starts: Sequence[int] | None = None) -> dict[str, dict[str, int]]:
        if line_starts is None:
            return {
                'start': {'offset': self.start},
                'end': {'offset': self.end},
            }
        return {
            'start': _point_ast_from_offset(line_starts, self.start),
            'end': _point_ast_from_offset(line_starts, self.end),
        }


NodeKind = TypingLiteral['node', 'parent', 'literal']


@dataclass(frozen=True)
class NodeSpec:
    """Static shape description for a Wenmode node class.

    :param type: mdast-compatible node type name.
    :param kind: Whether the node is a bare node, parent node, or literal node.
    :param fields: Node-specific dataclass fields beyond Wenmode's common
        fields for that node kind.
    """

    type: str
    kind: NodeKind
    fields: tuple[str, ...] = ()


@dataclass
class Node:
    """Base class for all Wenmode AST nodes.

    :param type: mdast-compatible node type name.
    :param data: Optional extension data used by transforms or renderers.
    :param position: Optional 0-based source offset range.
    """

    type: str
    data: dict[str, Any] | None = None
    position: Position | None = None

    @classmethod
    def to_spec(cls) -> NodeSpec:
        """Return a static specification for this node class.

        The specification is derived from dataclass fields and does not require
        constructing a node instance.
        """
        return node_spec_from_class(cls, kind='node', standard_fields={'type', 'data', 'position'})

    def to_ast(self) -> dict[str, Any]:
        """Convert this node and its children to plain Python data.

        Standalone nodes do not have root-level line-start context, so source
        positions are serialized with offsets only. Use ``Root.to_ast()`` on a
        parsed document root when you need unist-style ``line`` and ``column``
        fields.

        :returns: A dictionary made from strings, numbers, lists, and nested
            dictionaries.
        """
        return self._to_ast(None)

    def _to_ast(self, line_starts: Sequence[int] | None) -> dict[str, Any]:
        data: dict[str, Any] = {'type': self.type}
        for key, value in self.__dict__.items():
            if key == 'type' or key.startswith('_') or value is None:
                continue
            if isinstance(value, Position):
                data[key] = value.to_ast(line_starts)
                continue
            if isinstance(value, list):
                items: list[Any] = []
                for item in value:
                    if isinstance(item, Node):
                        items.append(item._to_ast(line_starts))
                    else:
                        items.append(item)
                data[key] = items
            elif isinstance(value, Node):
                data[key] = value._to_ast(line_starts)
            else:
                data[key] = value
        return data


def node_type_from_class(node_class: type[Node]) -> str:
    for item in fields(node_class):
        if item.name != 'type':
            continue
        if item.default is not MISSING:
            return str(item.default)
        raise TypeError(f'{node_class.__name__}.to_spec() requires a default type value')
    raise TypeError(f'{node_class.__name__}.to_spec() requires a type field')


@dataclass
class Parent(Node):
    """Base class for nodes that contain child nodes."""

    children: list[Node] = field(default_factory=list)

    @classmethod
    def to_spec(cls) -> NodeSpec:
        """Return a static specification for this parent node class."""
        return node_spec_from_class(cls, kind='parent', standard_fields={'type', 'data', 'position', 'children'})


@dataclass
class Literal(Node):
    """Base class for nodes that store literal text."""

    value: str = ''

    @classmethod
    def to_spec(cls) -> NodeSpec:
        """Return a static specification for this literal node class."""
        return node_spec_from_class(cls, kind='literal', standard_fields={'type', 'data', 'position', 'value'})


@dataclass
class Root(Parent):
    """Document root node."""

    _footnote_definitions: dict[str, FootnoteDefinition] | None = field(default=None, repr=False)
    _line_starts: list[int] | None = field(default=None, repr=False)
    type: str = 'root'

    def to_ast(self) -> dict[str, Any]:
        """Convert this root and its children to plain Python data.

        When the root was parsed with ``positions=True``, position offsets are
        converted to unist-style ``line`` and ``column`` fields.
        """
        return self._to_ast(self._line_starts)

    @property
    def footnote_definitions(self) -> dict[str, FootnoteDefinition] | None:
        """Collected footnote definitions, if the footnote transform ran."""
        return self._footnote_definitions

    @footnote_definitions.setter
    def footnote_definitions(self, definitions: dict[str, FootnoteDefinition] | None) -> None:
        self._footnote_definitions = definitions


def _point_ast_from_offset(line_starts: Sequence[int], offset: int) -> dict[str, int]:
    index = bisect.bisect_right(line_starts, offset) - 1
    if index < 0:
        index = 0
    return {
        'line': index + 1,
        'column': offset - line_starts[index] + 1,
        'offset': offset,
    }


def node_spec_from_class(node_class: type[Node], kind: NodeKind, standard_fields: set[str]) -> NodeSpec:
    custom_fields = tuple(
        item.name
        for item in fields(node_class)
        if item.name not in standard_fields and not item.name.startswith('_')
    )
    return NodeSpec(type=node_type_from_class(node_class), kind=kind, fields=custom_fields)


@dataclass
class Paragraph(Parent):
    """Paragraph node."""

    type: str = 'paragraph'


@dataclass
class Heading(Parent):
    """Heading node.

    :param depth: Heading depth from 1 through 6.
    """

    depth: int = 1
    type: str = 'heading'


@dataclass
class Blockquote(Parent):
    """Block quote container node."""

    type: str = 'blockquote'


@dataclass
class List(Parent):
    """Ordered or unordered list node."""

    ordered: bool = False
    start: int | None = None
    spread: bool = False
    type: str = 'list'


@dataclass
class ListItem(Parent):
    """List item node."""

    checked: bool | None = None
    spread: bool = False
    type: str = 'listItem'


@dataclass
class Code(Literal):
    """Fenced or indented code block node."""

    lang: str | None = None
    meta: str | None = None
    type: str = 'code'


@dataclass
class ThematicBreak(Node):
    """Thematic break node."""

    type: str = 'thematicBreak'


@dataclass
class Html(Literal):
    """Raw HTML node."""

    type: str = 'html'


@dataclass
class Text(Literal):
    """Plain text node."""

    _parse_emphasis: bool = True
    type: str = 'text'


@dataclass
class InlineCode(Literal):
    """Inline code span node."""

    type: str = 'inlineCode'


@dataclass
class Strong(Parent):
    """Strong emphasis node."""

    type: str = 'strong'


@dataclass
class Emphasis(Parent):
    """Emphasis node."""

    type: str = 'emphasis'


@dataclass
class Delete(Parent):
    """Deleted text node."""

    type: str = 'delete'


@dataclass
class Table(Parent):
    """Table node."""

    align: list[str | None] = field(default_factory=list)
    type: str = 'table'


@dataclass
class TableRow(Parent):
    """Table row node."""

    type: str = 'tableRow'


@dataclass
class TableCell(Parent):
    """Table cell node."""

    type: str = 'tableCell'


@dataclass
class Link(Parent):
    """Link node."""

    url: str = ''
    title: str | None = None
    type: str = 'link'


@dataclass
class Image(Node):
    """Image node."""

    url: str = ''
    alt: str = ''
    title: str | None = None
    type: str = 'image'


@dataclass
class Break(Node):
    """Hard line break node."""

    type: str = 'break'


@dataclass
class FootnoteReference(Node):
    """Footnote reference node."""

    identifier: str = ''
    label: str = ''
    type: str = 'footnoteReference'


@dataclass
class FootnoteDefinition(Parent):
    """Footnote definition node."""

    identifier: str = ''
    label: str = ''
    type: str = 'footnoteDefinition'


@dataclass
class TextDirective(Parent):
    """Inline directive node."""

    name: str = ''
    attributes: dict[str, str] | None = None
    type: str = 'textDirective'


@dataclass
class LeafDirective(Parent):
    """Leaf block directive node."""

    name: str = ''
    attributes: dict[str, str] | None = None
    type: str = 'leafDirective'


@dataclass
class ContainerDirective(Parent):
    """Container block directive node."""

    name: str = ''
    attributes: dict[str, str] | None = None
    type: str = 'containerDirective'


@dataclass
class LiteralDirective(Literal):
    """Literal block directive node."""

    name: str = ''
    argument: str | None = None
    attributes: dict[str, str] | None = None
    type: str = 'literalDirective'


DirectiveNode = TextDirective | LeafDirective | ContainerDirective | LiteralDirective

BUILTIN_NODES: list[type[Node]] = [
    Root,
    Paragraph,
    Heading,
    Blockquote,
    List,
    ListItem,
    Code,
    ThematicBreak,
    Html,
    Text,
    InlineCode,
    Strong,
    Emphasis,
    Delete,
    Table,
    TableRow,
    TableCell,
    Link,
    Image,
    Break,
    FootnoteReference,
    FootnoteDefinition,
    TextDirective,
    LeafDirective,
    ContainerDirective,
    LiteralDirective,
]
