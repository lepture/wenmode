from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import ClassVar, cast

from wenmode.nodes import Node


@dataclass
class RenderContext:
    pass


RenderHandler = Callable[..., str]


class BaseRenderer:
    handlers: ClassVar[dict[str, RenderHandler]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.handlers = dict(cls.handlers)

    def create_context(self, node: Node) -> RenderContext:
        return RenderContext()

    def render(self, node: Node, context: RenderContext | None = None) -> str:
        if context is None:
            context = self.create_context(node)
        return self.render_node(node, context)

    def render_node(self, node: Node, context: RenderContext) -> str:
        handler = self.handlers.get(node.type)
        if handler is None:
            return self.render_unknown(node, context)
        return handler(self, node, context)

    def render_children(self, children: list[Node], context: RenderContext) -> str:
        return ''.join(self.render_node(child, context) for child in children)

    @classmethod
    def register(cls, node_type: str) -> Callable[[RenderHandler], RenderHandler]:
        def decorator(handler: RenderHandler) -> RenderHandler:
            cls.handlers[node_type] = handler
            return handler

        return decorator

    def render_unknown(self, node: Node, context: RenderContext) -> str:
        children = getattr(node, 'children', None)
        if isinstance(children, list):
            return self.render_children(cast(list[Node], children), context)

        value = getattr(node, 'value', None)
        if isinstance(value, str):
            return value

        return ''
