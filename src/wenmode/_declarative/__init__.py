from __future__ import annotations

from .install import install_declarative as install_declarative
from .spec import DeclarativePluginSpec as DeclarativePluginSpec
from .spec import InlineDelimited as InlineDelimited
from .spec import RenderTemplate as RenderTemplate

__all__ = ['DeclarativePluginSpec', 'InlineDelimited', 'RenderTemplate', 'install_declarative']
