from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import ModuleType
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

from wenmode.renderers.base import RenderHandler

if TYPE_CHECKING:
    from wenmode.wenmode import Wenmode
else:
    Wenmode = Any

RendererHandlers: TypeAlias = Mapping[str, Mapping[str, RenderHandler]]


class Plugin(Protocol):
    """Protocol for objects installable through ``Wenmode`` plugins."""

    def setup(self, wenmode: Wenmode, **options: Any) -> None:
        """Install parser rules, renderer handlers, or other behavior."""
        pass


PluginLike: TypeAlias = Plugin | ModuleType


@dataclass(frozen=True)
class PluginSpec:
    """Plugin plus setup options for constructor-time installation."""

    target: PluginLike
    options: Mapping[str, Any]


PluginTarget: TypeAlias = PluginLike | PluginSpec


def plugin(target: PluginLike, **options: Any) -> PluginSpec:
    """Return a plugin specification that carries setup options."""
    return PluginSpec(target=target, options=dict(options))


class _PluginSetup(Protocol):
    """Callable shape of a plugin ``setup`` function."""

    def __call__(self, wenmode: Wenmode, **options: Any) -> None:
        """Install plugin behavior on a :class:`wenmode.Wenmode` instance."""
        pass
