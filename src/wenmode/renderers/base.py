from __future__ import annotations

from collections.abc import Callable
from typing import ClassVar, cast

from wenmode.nodes import Node

RenderHandler = Callable[..., str]


class BaseRenderer:
    handlers: ClassVar[dict[str, RenderHandler]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.handlers = dict(cls.handlers)

    def render(self, node: Node) -> str:
        handler = self.handlers.get(node.type)
        if handler is None:
            return self.render_unknown(node)
        return handler(self, node)

    def render_children(self, children: list[Node]) -> str:
        return ''.join(self.render(child) for child in children)

    @classmethod
    def register(cls, node_type: str) -> Callable[[RenderHandler], RenderHandler]:
        def decorator(handler: RenderHandler) -> RenderHandler:
            cls.handlers[node_type] = handler
            return handler

        return decorator

    def render_unknown(self, node: Node) -> str:
        children = getattr(node, 'children', None)
        if isinstance(children, list):
            return self.render_children(cast(list[Node], children))

        value = getattr(node, 'value', None)
        if isinstance(value, str):
            return value

        return ''
