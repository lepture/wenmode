from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, cast

T = TypeVar('T')


@dataclass(frozen=True)
class StateKey(Generic[T]):
    """Typed key for per-parse extension state.

    Rules and transforms should use ``StateKey`` instead of storing mutable
    per-document data on rule instances.

    :param name: Unique key name. Use a package-qualified name to avoid
        collisions.
    :param factory: Callable that creates the initial value for each parse.
    """

    name: str
    factory: Callable[[], T]


class StateStore:
    """Per-parse storage for extension state."""

    def __init__(self) -> None:
        self._values: dict[str, Any] = {}

    def get(self, key: StateKey[T]) -> T:
        """Return the value for a key, creating it if necessary.

        :param key: State key to read.
        :returns: Stored value for this parse.
        """
        if key.name not in self._values:
            self._values[key.name] = key.factory()
        return cast(T, self._values[key.name])

    def set(self, key: StateKey[T], value: T) -> None:
        """Store a value for a key in this parse."""
        self._values[key.name] = value
