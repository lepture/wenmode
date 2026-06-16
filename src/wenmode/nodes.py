from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Node:
    type: str

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
    type: str = 'paragraph'


@dataclass
class Heading(Parent):
    depth: int = 1
    type: str = 'heading'


@dataclass
class Blockquote(Parent):
    type: str = 'blockquote'


@dataclass
class List(Parent):
    ordered: bool = False
    start: int | None = None
    spread: bool = False
    type: str = 'list'


@dataclass
class ListItem(Parent):
    spread: bool = False
    type: str = 'listItem'


@dataclass
class Code(Literal):
    lang: str | None = None
    meta: str | None = None
    type: str = 'code'


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
class Strong(Parent):
    type: str = 'strong'


@dataclass
class Emphasis(Parent):
    type: str = 'emphasis'


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
