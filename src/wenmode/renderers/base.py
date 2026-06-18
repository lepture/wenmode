from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator
from dataclasses import dataclass
from typing import ClassVar, cast

from wenmode.nodes import Node


@dataclass
class RenderContext:
    """Base render context passed through renderer handlers."""

    pass


RenderHandler = Callable[..., str]


class BaseRenderer:
    """Dispatch-based base class for renderers.

    Subclasses register handlers with :meth:`register`. A handler receives the
    renderer instance, the node, and the render context, and returns rendered
    text.
    """

    handlers: ClassVar[dict[str, RenderHandler]] = {}

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.handlers = dict(cls.handlers)

    def create_context(self, node: Node | None = None) -> RenderContext:
        """Create a render context for one render call.

        :param node: Root node being rendered, when available.
        :returns: New render context.
        """
        return RenderContext()

    def render(self, node: Node, context: RenderContext | None = None) -> str:
        """Render a node.

        :param node: Node to render.
        :param context: Optional render context. When omitted, a new context is
            created.
        :returns: Rendered output.
        """
        if context is None:
            context = self.create_context(node)
        return self.render_node(node, context)

    def render_iter(self, nodes: Iterable[Node]) -> Iterator[str]:
        """Render an iterable of nodes with one shared context.

        :param nodes: Nodes to render.
        :returns: Iterator of rendered chunks.
        """
        context = self.create_context()
        for node in nodes:
            yield self.render_node(node, context)

    def render_node(self, node: Node, context: RenderContext) -> str:
        """Render one node with an existing context."""
        handler = self.handlers.get(node.type)
        if handler is None:
            return self.render_unknown(node, context)
        return handler(self, node, context)

    def render_children(self, children: list[Node], context: RenderContext) -> str:
        """Render child nodes and concatenate their output."""
        return ''.join(self.render_node(child, context) for child in children)

    @classmethod
    def register(cls, node_type: str) -> Callable[[RenderHandler], RenderHandler]:
        """Register a render handler for a node type.

        :param node_type: Value of ``node.type`` handled by the decorated
            function.
        :returns: Decorator that stores the handler on the renderer class.
        """
        def decorator(handler: RenderHandler) -> RenderHandler:
            cls.handlers[node_type] = handler
            return handler

        return decorator

    def render_unknown(self, node: Node, context: RenderContext) -> str:
        """Render a node without a registered handler.

        The default behavior renders child nodes, then literal ``value`` fields,
        and otherwise returns an empty string.
        """
        children = getattr(node, 'children', None)
        if isinstance(children, list):
            return self.render_children(cast(list[Node], children), context)

        value = getattr(node, 'value', None)
        if isinstance(value, str):
            return value

        return ''
