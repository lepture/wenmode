from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    type: str
    data: dict[str, Any] | None = None

    def to_ast(self) -> dict[str, Any]:
        data: dict[str, Any] = {'type': self.type}
        for key, value in self.__dict__.items():
            if key == 'type' or key.startswith('_') or value is None:
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
    children: list[Node] = field(default_factory=list)


@dataclass
class Literal(Node):
    value: str = ''


@dataclass
class Root(Parent):
    _footnote_definitions: dict[str, FootnoteDefinition] | None = field(default=None, repr=False)
    type: str = 'root'

    @property
    def footnote_definitions(self) -> dict[str, FootnoteDefinition] | None:
        return self._footnote_definitions

    @footnote_definitions.setter
    def footnote_definitions(self, definitions: dict[str, FootnoteDefinition] | None) -> None:
        self._footnote_definitions = definitions


@dataclass
class Paragraph(Parent):
    type: str = 'paragraph'


@dataclass
class Heading(Parent):
    depth: int = 1
    type: str = 'heading'


@dataclass
class Blockquote(Parent):
    type: str = 'blockquote'


@dataclass
class BlockSpoiler(Parent):
    type: str = 'blockSpoiler'


@dataclass
class List(Parent):
    ordered: bool = False
    start: int | None = None
    spread: bool = False
    type: str = 'list'


@dataclass
class ListItem(Parent):
    checked: bool | None = None
    spread: bool = False
    type: str = 'listItem'


@dataclass
class DefinitionList(Parent):
    type: str = 'definitionList'


@dataclass
class DefinitionTerm(Parent):
    type: str = 'definitionTerm'


@dataclass
class DefinitionDescription(Parent):
    spread: bool = False
    type: str = 'definitionDescription'


@dataclass
class Code(Literal):
    lang: str | None = None
    meta: str | None = None
    type: str = 'code'


@dataclass
class Math(Literal):
    type: str = 'math'


@dataclass
class ThematicBreak(Node):
    type: str = 'thematicBreak'


@dataclass
class Html(Literal):
    type: str = 'html'


@dataclass
class Text(Literal):
    _parse_emphasis: bool = True
    type: str = 'text'


@dataclass
class InlineCode(Literal):
    type: str = 'inlineCode'


@dataclass
class InlineMath(Literal):
    type: str = 'inlineMath'


@dataclass
class Strong(Parent):
    type: str = 'strong'


@dataclass
class Emphasis(Parent):
    type: str = 'emphasis'


@dataclass
class Delete(Parent):
    type: str = 'delete'


@dataclass
class Mark(Parent):
    type: str = 'mark'


@dataclass
class Insert(Parent):
    type: str = 'insert'


@dataclass
class Superscript(Parent):
    type: str = 'superscript'


@dataclass
class Subscript(Parent):
    type: str = 'subscript'


@dataclass
class Ruby(Node):
    segments: list[dict[str, str]] = field(default_factory=list)
    type: str = 'ruby'


@dataclass
class InlineSpoiler(Parent):
    type: str = 'inlineSpoiler'


@dataclass
class Abbreviation(Parent):
    title: str = ''
    type: str = 'abbreviation'


@dataclass
class Table(Parent):
    align: list[str | None] = field(default_factory=list)
    type: str = 'table'


@dataclass
class TableRow(Parent):
    type: str = 'tableRow'


@dataclass
class TableCell(Parent):
    type: str = 'tableCell'


@dataclass
class Link(Parent):
    url: str = ''
    title: str | None = None
    type: str = 'link'


@dataclass
class Image(Node):
    url: str = ''
    alt: str = ''
    title: str | None = None
    type: str = 'image'


@dataclass
class Break(Node):
    type: str = 'break'


@dataclass
class FootnoteReference(Node):
    identifier: str = ''
    label: str = ''
    type: str = 'footnoteReference'


@dataclass
class FootnoteDefinition(Parent):
    identifier: str = ''
    label: str = ''
    type: str = 'footnoteDefinition'


@dataclass
class TextDirective(Parent):
    name: str = ''
    attributes: dict[str, str] | None = None
    type: str = 'textDirective'


@dataclass
class LeafDirective(Parent):
    name: str = ''
    attributes: dict[str, str] | None = None
    type: str = 'leafDirective'


@dataclass
class ContainerDirective(Parent):
    name: str = ''
    attributes: dict[str, str] | None = None
    type: str = 'containerDirective'


DirectiveNode = TextDirective | LeafDirective | ContainerDirective
