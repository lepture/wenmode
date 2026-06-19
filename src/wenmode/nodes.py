from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
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


@dataclass(frozen=True)
class Position:
    """Source range for a node."""

    start: Point
    end: Point

    def to_ast(self) -> dict[str, dict[str, int]]:
        return {
            'start': self.start.to_ast(),
            'end': self.end.to_ast(),
        }


def advance_point(point: Point, text: str) -> Point:
    """Return the point reached after consuming ``text``."""
    line = point.line
    column = point.column
    offset = point.offset
    for char in text:
        offset += 1
        if char == '\n':
            line += 1
            column = 1
        else:
            column += 1
    return Point(line=line, column=column, offset=offset)


def position_from_offsets(position: Position | None, text: str, start: int, end: int) -> Position | None:
    """Return a position for ``text[start:end]`` within an existing position."""
    if position is None:
        return None
    start_point = advance_point(position.start, text[:start])
    end_point = advance_point(start_point, text[start:end])
    return Position(start=start_point, end=end_point)


@dataclass
class Node:
    """Base class for all Wenmode AST nodes.

    :param type: mdast-compatible node type name.
    :param data: Optional extension data used by transforms or renderers.
    :param position: Optional unist-style source range.
    """

    type: str
    data: dict[str, Any] | None = None
    position: Position | None = None

    def to_ast(self) -> dict[str, Any]:
        """Convert this node and its children to plain Python data.

        :returns: A dictionary made from strings, numbers, lists, and nested
            dictionaries.
        """
        data: dict[str, Any] = {'type': self.type}
        for key, value in self.__dict__.items():
            if key == 'type' or key.startswith('_') or value is None:
                continue
            if isinstance(value, Position):
                data[key] = value.to_ast()
                continue
            if isinstance(value, list):
                data[key] = [item.to_ast() if isinstance(item, Node) else item for item in value]
            elif isinstance(value, Node):
                data[key] = value.to_ast()
            else:
                data[key] = value
        return data


@dataclass
class Parent(Node):
    """Base class for nodes that contain child nodes."""

    children: list[Node] = field(default_factory=list)


@dataclass
class Literal(Node):
    """Base class for nodes that store literal text."""

    value: str = ''


@dataclass
class Root(Parent):
    """Document root node."""

    _footnote_definitions: dict[str, FootnoteDefinition] | None = field(default=None, repr=False)
    type: str = 'root'

    @property
    def footnote_definitions(self) -> dict[str, FootnoteDefinition] | None:
        """Collected footnote definitions, if the footnote transform ran."""
        return self._footnote_definitions

    @footnote_definitions.setter
    def footnote_definitions(self, definitions: dict[str, FootnoteDefinition] | None) -> None:
        self._footnote_definitions = definitions


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


DirectiveNode = TextDirective | LeafDirective | ContainerDirective
