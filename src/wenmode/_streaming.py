from __future__ import annotations

from collections.abc import Iterable


class StreamingUnsupportedError(RuntimeError):
    """Raised when a rule set or renderer cannot be used for streaming output."""


def unique_blockers(blockers: Iterable[str]) -> list[str]:
    """Return blocker names in first-seen order without duplicates."""
    unique: list[str] = []
    for blocker in blockers:
        if blocker not in unique:
            unique.append(blocker)
    return unique


def assert_streaming_supported(blockers: Iterable[str], *, blocked_by: str, guidance: str | None = None) -> None:
    names = ', '.join(unique_blockers(blockers))
    if not names:
        return
    message = f'streaming output is blocked by {blocked_by}: {names}'
    if guidance:
        message = f'{message}; {guidance}'
    raise StreamingUnsupportedError(message)
