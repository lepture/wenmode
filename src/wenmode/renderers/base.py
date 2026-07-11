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
RootRenderHook = Callable[..., str]
ROOT_PRE_HANDLER = 'root:pre'
ROOT_POST_HANDLER = 'root:post'


def render_node_children(renderer: BaseRenderer, node: Node, context: RenderContext) -> str:
    """Render child nodes for handlers that intentionally collapse a wrapper."""
    children = getattr(node, 'children', None)
    if isinstance(children, list):
        return renderer.render_children(cast(list[Node], children), context)
    return ''


class BaseRenderer:
    """Dispatch-based base class for renderers.

    Subclasses register handlers with :meth:`register`. A handler receives the
    renderer instance, the node, and the render context, and returns rendered
    text.
    """

    name: ClassVar[str] = 'base'
    handlers: ClassVar[dict[str, RenderHandler]] = {}
    root_pre_renderers: ClassVar[list[RootRenderHook]] = []
    root_post_renderers: ClassVar[list[RootRenderHook]] = []
    streaming_safe_to_omit_class_root_hooks: ClassVar[bool] = False

    def __init__(self) -> None:
        self._handlers: dict[str, RenderHandler] = dict(self.handlers)
        self._root_pre_renderers = list(self.root_pre_renderers)
        self._root_post_renderers = list(self.root_post_renderers)
        self._class_root_pre_count = len(self._root_pre_renderers)
        self._class_root_post_count = len(self._root_post_renderers)
        self._dynamic_root_hook_blockers: set[str] = set()

    def __init_subclass__(cls) -> None:
        super().__init_subclass__()
        cls.handlers = dict(cls.handlers)
        cls.root_pre_renderers = list(cls.root_pre_renderers)
        cls.root_post_renderers = list(cls.root_post_renderers)
        if 'streaming_safe_to_omit_class_root_hooks' not in cls.__dict__:
            cls.streaming_safe_to_omit_class_root_hooks = False

    @property
    def supports_streaming(self) -> bool:
        """Return whether this renderer can omit root hooks during streaming."""
        return not self.streaming_blockers()

    def streaming_blockers(self) -> list[str]:
        """Return root hook labels that prevent streaming output."""
        blockers: list[str] = []
        if not self.streaming_safe_to_omit_class_root_hooks:
            if self._class_root_pre_count:
                blockers.append(ROOT_PRE_HANDLER)
            if self._class_root_post_count:
                blockers.append(ROOT_POST_HANDLER)
        for label in (ROOT_PRE_HANDLER, ROOT_POST_HANDLER):
            if label in self._dynamic_root_hook_blockers and label not in blockers:
                blockers.append(label)
        return blockers

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
        if node.type == 'root':
            return self.render_root(node, context)
        return self.render_node(node, context)

    def render_root(self, node: Node, context: RenderContext) -> str:
        """Render a root node with registered root pre/post render hooks."""
        parts = [hook(self, node, context) for hook in self._root_pre_renderers]
        parts.append(self.render_node(node, context))
        parts.extend(hook(self, node, context) for hook in self._root_post_renderers)
        return ''.join(parts)

    def render_iter(self, nodes: Iterable[Node]) -> Iterator[str]:
        """Render an iterable of nodes with one shared context.

        :param nodes: Nodes to render.
        :returns: Iterator of rendered chunks.
        """
        self._assert_streaming_supported()
        context = self.create_context()
        for node in nodes:
            yield self.render_node(node, context)

    def render_node(self, node: Node, context: RenderContext) -> str:
        """Render one node with an existing context."""
        handler = self._handlers.get(node.type)
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
            function. Use ``root:pre`` or ``root:post`` for root-level hooks.
        :returns: Decorator that stores the handler on the renderer class.
        """

        def decorator(handler: RenderHandler) -> RenderHandler:
            if node_type == ROOT_PRE_HANDLER:
                cls.root_pre_renderers.append(handler)
                return handler
            if node_type == ROOT_POST_HANDLER:
                cls.root_post_renderers.append(handler)
                return handler
            cls.handlers[node_type] = handler
            return handler

        return decorator

    def register_handler(self, node_type: str, handler: RenderHandler) -> None:
        """Register a render handler or root-level hook on this renderer instance."""
        if node_type == ROOT_PRE_HANDLER:
            self._root_pre_renderers.append(handler)
            self._dynamic_root_hook_blockers.add(ROOT_PRE_HANDLER)
            return
        if node_type == ROOT_POST_HANDLER:
            self._root_post_renderers.append(handler)
            self._dynamic_root_hook_blockers.add(ROOT_POST_HANDLER)
            return
        self._handlers[node_type] = handler

    def _assert_streaming_supported(self) -> None:
        blockers = self.streaming_blockers()
        if not blockers:
            return
        from wenmode.parser import StreamingUnsupportedError

        names = ', '.join(blockers)
        raise StreamingUnsupportedError(f'streaming output is blocked by root render hooks: {names}')

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
