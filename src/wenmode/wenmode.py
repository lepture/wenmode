from __future__ import annotations

from collections.abc import Iterable, Iterator

from .nodes import Node, Root
from .parser import Parser
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
    :param positions: Attach source positions to parsed nodes when ``True``.
    """

    def __init__(
        self,
        rules: Iterable[type[Rule] | Rule] | None = None,
        renderer: BaseRenderer | None = None,
        directives: Iterable[DirectiveHtmlRenderer] = (),
        positions: bool = False,
    ) -> None:
        self.parser = Parser(commonmark if rules is None else rules, positions=positions)
        self.renderer = renderer if renderer is not None else HTMLRenderer(directives=directives)
        if renderer is not None:
            for directive in directives:
                self.register_directive_renderer(directive)

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
