from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.rules.base import Rule

from .block import _block_rule_from_syntax
from .inline import _inline_rule_from_syntax
from .render import renderer_handlers_from_templates
from .spec import BlockFenced, DeclarativePluginSpec, InlineDelimited, InlineLiteral

if TYPE_CHECKING:
    from wenmode import Wenmode


def install_declarative(wen: Wenmode, spec: DeclarativePluginSpec) -> None:
    """Install a declarative plugin spec into a ``Wenmode`` instance."""

    rules: list[type[Rule] | Rule] = [_rule_from_syntax(syntax) for syntax in spec.syntax]
    if rules:
        wen.register_rules(rules)
    wen.register_renderer_handlers(renderer_handlers_from_templates(spec.renderers))


def _rule_from_syntax(syntax: BlockFenced | InlineDelimited | InlineLiteral) -> Rule:
    if isinstance(syntax, BlockFenced):
        return _block_rule_from_syntax(syntax)
    return _inline_rule_from_syntax(syntax)
