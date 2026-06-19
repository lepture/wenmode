from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol

from wenmode.renderers.base import RenderHandler

if TYPE_CHECKING:
    from wenmode import Wenmode

RendererHandlers = Mapping[str, Mapping[str, RenderHandler]]


class Plugin(Protocol):
    """Protocol for objects installable with :meth:`wenmode.Wenmode.use`."""

    def setup(self, wenmode: Wenmode, **options: Any) -> None:
        """Install parser rules, renderer handlers, or other behavior."""
        pass


class PluginSetup(Protocol):
    """Callable shape of a plugin ``setup`` function."""

    def __call__(self, wenmode: Wenmode, **options: Any) -> None:
        """Install plugin behavior on a :class:`wenmode.Wenmode` instance."""
        pass
