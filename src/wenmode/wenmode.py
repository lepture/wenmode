from __future__ import annotations

from collections.abc import Iterable, Iterator
from typing import Any, cast

from .nodes import Node, Root
from .parser import Parser
from .plugins import PluginTarget, RendererHandlers
from .plugins.types import PluginLike, PluginSpec, _PluginSetup
from .presets import commonmark
from .renderers import BaseRenderer, DirectiveHtmlRenderer, HTMLRenderer
from .rules.base import Rule
from .state import LineSource


class Wenmode:
    """Convenience facade that combines a parser and a renderer.

    ``Wenmode`` is the main high-level API for applications. It parses Markdown
    with a configured rule set and renders the resulting node tree with a
    renderer.

    :param rules: Rule classes or configured rule instances. When omitted, the
        CommonMark-style preset is used.
    :param renderer: Renderer instance used by :meth:`render` and
        :meth:`render_node`. When omitted, :class:`~wenmode.HTMLRenderer` is
        used.
    :param directives: HTML directive renderers to register on the default or
        supplied HTML renderer.
    :param plugins: Plugin modules or plugin objects to install during
        initialization.
    :param positions: Attach source positions to parsed nodes when ``True``.
    """

    def __init__(
        self,
        rules: Iterable[type[Rule] | Rule] | None = None,
        renderer: BaseRenderer | None = None,
        directives: Iterable[DirectiveHtmlRenderer] = (),
        plugins: Iterable[PluginTarget] = (),
        positions: bool = False,
    ) -> None:
        parser_rules: Iterable[type[Rule] | Rule]
        if rules is None:
            parser_rules = commonmark
        else:
            parser_rules = rules
        self.parser = Parser(parser_rules, positions=positions)
        if renderer is not None:
            self.renderer = renderer
        else:
            self.renderer = HTMLRenderer(directives=directives)
        if renderer is not None:
            for directive in directives:
                self.register_directive_renderer(directive)
        for plugin in plugins:
            self.use(plugin)

    def parse(self, source: LineSource) -> Root:
        """Parse Markdown into a root node.

        :param source: Markdown source as a string or an iterable of lines.
        :returns: Parsed document root.
        """
        return self.parser.parse(source)

    def render(self, source: LineSource) -> str:
        """Parse Markdown and render it with the configured renderer.

        :param source: Markdown source as a string or an iterable of lines.
        :returns: Rendered output.
        """
        return self.render_node(self.parse(source))

    def render_node(self, node: Node) -> str:
        """Render an existing AST node.

        :param node: Node to render.
        :returns: Rendered output.
        """
        return self.renderer.render(node)

    def stream(self, source: LineSource) -> Iterator[str]:
        """Yield rendered chunks while parsing Markdown incrementally.

        Streaming is only supported for rule sets that do not require deferred
        document-wide inline transforms.

        :param source: Markdown source as a string or an iterable of lines.
        :returns: Iterator of rendered chunks.
        :raises wenmode.StreamingUnsupportedError: Raised by the parser when a
            configured rule set requires deferred inline resolution.
        """
        return self.renderer.render_iter(self.parser.parse_iter(source))

    def register_rule(self, rule: type[Rule] | Rule) -> None:
        """Register or replace one parser rule.

        :param rule: Rule class or configured rule instance.
        """
        self.parser.register_rule(rule)

    def register_rules(self, rules: Iterable[type[Rule] | Rule]) -> None:
        """Register or replace multiple parser rules.

        :param rules: Rule classes or configured rule instances.
        """
        self.parser.register_rules(rules)

    def register_renderer_handlers(self, handlers: RendererHandlers) -> None:
        """Register renderer handlers for the configured renderer.

        The mapping is keyed by renderer name, then node type. Handlers for other
        renderer names are ignored.
        """
        renderer_handlers = handlers.get(self.renderer.name)
        if renderer_handlers is None:
            return
        for node_type, handler in renderer_handlers.items():
            self.renderer.register_handler(node_type, handler)

    def register_directive_renderer(self, directive: DirectiveHtmlRenderer) -> None:
        """Register an HTML directive renderer.

        :param directive: Directive renderer implementing
            :class:`~wenmode.renderers.html.DirectiveHtmlRenderer`.
        :raises TypeError: If this ``Wenmode`` instance does not use an
            :class:`~wenmode.HTMLRenderer`.
        """
        if not isinstance(self.renderer, HTMLRenderer):
            raise TypeError('directive renderers require an HTMLRenderer')
        self.renderer.register_directive_renderer(directive)

    def use(self, plugin: PluginTarget, **options: Any) -> Wenmode:
        """Install a plugin module or plugin object on this parser and renderer."""
        target: PluginLike
        if isinstance(plugin, PluginSpec):
            if options:
                raise TypeError('plugin specs cannot be combined with extra options')
            target = plugin.target
            options = dict(plugin.options)
        else:
            target = plugin

        setup = getattr(target, 'setup', None)
        if not callable(setup):
            raise TypeError('plugins must define setup(wenmode, **options)')
        cast(_PluginSetup, setup)(self, **options)
        return self
