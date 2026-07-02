from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wenmode.rules.base import Rule

from .inline import _inline_rule_from_syntax
from .render import renderer_handlers_from_templates
from .spec import DeclarativePluginSpec

if TYPE_CHECKING:
    from wenmode import Wenmode


def install_declarative(wenmode: Wenmode, spec: DeclarativePluginSpec, **options: Any) -> None:
    """Install a declarative plugin spec into a ``Wenmode`` instance."""

    if options:
        option_names = ', '.join(sorted(options))
        raise TypeError(f'declarative plugin {spec.name!r} does not accept setup options: {option_names}')

    rules: list[type[Rule] | Rule] = [_inline_rule_from_syntax(syntax) for syntax in spec.syntax]
    if rules:
        wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(renderer_handlers_from_templates(spec.renderers))
