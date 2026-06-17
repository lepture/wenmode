from __future__ import annotations

from collections.abc import Iterable

from .nodes import Node, Root
from .parser import Parser
from .presets import commonmark
from .renderers import BaseRenderer, DirectiveHtmlRenderer, HTMLRenderer
from .rules.base import Rule
from .state import LineSource


class Wenmode:
    def __init__(
        self,
        rules: Iterable[type[Rule] | Rule] | None = None,
        renderer: BaseRenderer | None = None,
        directives: Iterable[DirectiveHtmlRenderer] = (),
    ) -> None:
        self.parser = Parser(commonmark if rules is None else rules)
        self.renderer = renderer if renderer is not None else HTMLRenderer(directives=directives)
        if renderer is not None:
            for directive in directives:
                self.register_directive_renderer(directive)

    def parse(self, source: LineSource) -> Root:
        return self.parser.parse(source)

    def render(self, node: Node) -> str:
        return self.renderer.render(node)

    def register_rule(self, rule: type[Rule] | Rule) -> None:
        self.parser.register_rule(rule)

    def register_rules(self, rules: Iterable[type[Rule] | Rule]) -> None:
        self.parser.register_rules(rules)

    def register_directive_renderer(self, directive: DirectiveHtmlRenderer) -> None:
        if not isinstance(self.renderer, HTMLRenderer):
            raise TypeError('directive renderers require an HTMLRenderer')
        self.renderer.register_directive_renderer(directive)
