from __future__ import annotations

from collections.abc import Mapping
from typing import TYPE_CHECKING, Any, Protocol, TypeAlias

from wenmode.renderers import RenderHandler

if TYPE_CHECKING:
    from wenmode.wenmode import Wenmode
else:
    Wenmode = Any

RendererHandlers: TypeAlias = Mapping[str, Mapping[str, RenderHandler]]


class PluginModule(Protocol):
    """Protocol for objects installable through ``Wenmode`` plugins."""

    def setup(self, wen: Wenmode, /) -> None:
        """Install parser rules, renderer handlers, or other behavior."""
        pass
