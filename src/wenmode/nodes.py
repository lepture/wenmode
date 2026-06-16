from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

HtmlAttrValue = str | int | bool | None


@dataclass
class Node:
    html_tag: ClassVar[str | None] = None
    html_void: ClassVar[bool] = False
    block: ClassVar[bool] = False
    type: str

    def get_html_tag(self) -> str | None:
        return self.html_tag

    def get_html_attrs(self) -> dict[str, HtmlAttrValue]:
        return {}

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
    type: str = 'root'


@dataclass
class Paragraph(Parent):
    html_tag: ClassVar[str | None] = 'p'
    block: ClassVar[bool] = True
    type: str = 'paragraph'


@dataclass
class Heading(Parent):
    block: ClassVar[bool] = True
    depth: int = 1
    type: str = 'heading'

    def get_html_tag(self) -> str:
        return f'h{self.depth}'


@dataclass
class Blockquote(Parent):
    block: ClassVar[bool] = True
    type: str = 'blockquote'


@dataclass
class List(Parent):
    block: ClassVar[bool] = True
    ordered: bool = False
    start: int | None = None
    spread: bool = False
    type: str = 'list'


@dataclass
class ListItem(Parent):
    block: ClassVar[bool] = True
    checked: bool | None = None
    spread: bool = False
    type: str = 'listItem'


@dataclass
class Code(Literal):
    block: ClassVar[bool] = True
    lang: str | None = None
    meta: str | None = None
    type: str = 'code'


@dataclass
class Math(Literal):
    block: ClassVar[bool] = True
    type: str = 'math'


@dataclass
class ThematicBreak(Node):
    html_tag: ClassVar[str | None] = 'hr'
    html_void: ClassVar[bool] = True
    block: ClassVar[bool] = True
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
    html_tag: ClassVar[str | None] = 'code'
    type: str = 'inlineCode'


@dataclass
class InlineMath(Literal):
    type: str = 'inlineMath'


@dataclass
class Strong(Parent):
    html_tag: ClassVar[str | None] = 'strong'
    type: str = 'strong'


@dataclass
class Emphasis(Parent):
    html_tag: ClassVar[str | None] = 'em'
    type: str = 'emphasis'


@dataclass
class Delete(Parent):
    html_tag: ClassVar[str | None] = 'del'
    type: str = 'delete'


@dataclass
class Table(Parent):
    block: ClassVar[bool] = True
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
    html_tag: ClassVar[str | None] = 'a'
    url: str = ''
    title: str | None = None
    type: str = 'link'

    def get_html_attrs(self) -> dict[str, HtmlAttrValue]:
        attrs: dict[str, HtmlAttrValue] = {'href': self.url}
        if self.title:
            attrs['title'] = self.title
        return attrs


@dataclass
class Image(Node):
    html_tag: ClassVar[str | None] = 'img'
    html_void: ClassVar[bool] = True
    url: str = ''
    alt: str = ''
    title: str | None = None
    type: str = 'image'

    def get_html_attrs(self) -> dict[str, HtmlAttrValue]:
        attrs: dict[str, HtmlAttrValue] = {'src': self.url, 'alt': self.alt}
        if self.title:
            attrs['title'] = self.title
        return attrs


@dataclass
class Break(Node):
    html_tag: ClassVar[str | None] = 'br'
    html_void: ClassVar[bool] = True
    type: str = 'break'


@dataclass
class FootnoteReference(Node):
    identifier: str = ''
    label: str = ''
    type: str = 'footnoteReference'


@dataclass
class FootnoteDefinition(Parent):
    block: ClassVar[bool] = True
    identifier: str = ''
    label: str = ''
    type: str = 'footnoteDefinition'
