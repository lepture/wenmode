from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

from wenmode.renderers import RenderHandler

from .._declarative import DeclarativePluginSpec

if TYPE_CHECKING:
    from wenmode.wenmode import Wenmode
else:
    Wenmode = Any

RendererHandlers: TypeAlias = Mapping[str, Mapping[str, RenderHandler]]


class SetupPluginModule(Protocol):
    """Protocol for objects installable through ``Wenmode`` plugins."""

    def setup(self, wen: Wenmode, **options: Any) -> None:
        """Install parser rules, renderer handlers, or other behavior."""
        pass


class DeclarativePluginModule(Protocol):
    """Protocol for plugin modules exposing a declarative spec."""

    spec: DeclarativePluginSpec


PluginLike: TypeAlias = SetupPluginModule | DeclarativePluginModule | ModuleType


@dataclass(frozen=True)
class PluginConfig:
    """Plugin plus setup options for constructor-time installation."""

    target: PluginLike
    options: Mapping[str, Any]


PluginTarget: TypeAlias = PluginLike | PluginConfig


def plugin(target: PluginLike, **options: Any) -> PluginConfig:
    """Return a plugin configuration that carries setup options."""
    return PluginConfig(target=target, options=dict(options))


class _PluginSetup(Protocol):
    """Callable shape of a plugin ``setup`` function."""

    def __call__(self, wen: Wenmode, **options: Any) -> None:
        """Install plugin behavior on a :class:`wenmode.Wenmode` instance."""
        pass
