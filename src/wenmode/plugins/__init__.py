"""Built-in Wenmode plugins and plugin API types."""

from typing import Any

from .._declarative import BlockFenced as BlockFenced
from .._declarative import DeclarativePluginSpec as DeclarativePluginSpec
from .._declarative import InlineDelimited as InlineDelimited
from .._declarative import InlineLiteral as InlineLiteral
from .._declarative import RendererFallback as RendererFallback
from .._declarative import RenderTemplate as RenderTemplate
from .._declarative import install_declarative as install_declarative
from .types import PluginConfig, PluginLike
from .types import RendererHandlers as RendererHandlers


def plugin(target: PluginLike, **options: Any) -> PluginConfig:
    """Return a plugin configuration that carries setup options."""
    return PluginConfig(target=target, options=dict(options))


__all__ = [
    'BlockFenced',
    'DeclarativePluginSpec',
    'InlineDelimited',
    'InlineLiteral',
    'RendererHandlers',
    'RendererFallback',
    'RenderTemplate',
    'install_declarative',
    'plugin',
]
