from __future__ import annotations

import warnings
from collections.abc import Callable, Iterable
from typing import cast

from .rules import (
    AtxHeading,
    Autolink,
    BackslashEscape,
    Blockquote,
    CharacterReference,
    Emphasis,
    ExtendedAutolink,
    FencedCode,
    Footnote,
    HardBreak,
    HtmlBlock,
    Image,
    IndentedCode,
    InlineCode,
    Link,
    List,
    RawHtml,
    Rule,
    SetextHeading,
    Strikethrough,
    Table,
    ThematicBreak,
)

RuleSpec = type[Rule] | Rule
PresetFactory = Callable[[], tuple[RuleSpec, ...]]

GFM_DISALLOWED_HTML_TAGS: tuple[str, ...] = (
    'title',
    'textarea',
    'style',
    'xmp',
    'iframe',
    'noembed',
    'noframes',
    'script',
    'plaintext',
)


def commonmark() -> tuple[RuleSpec, ...]:
    """Create the CommonMark-oriented rule preset."""
    return (
        ThematicBreak,
        FencedCode,
        IndentedCode,
        HtmlBlock,
        List,
        AtxHeading,
        SetextHeading,
        Blockquote,
        HardBreak,
        Autolink,
        RawHtml,
        BackslashEscape,
        CharacterReference,
        Image,
        Link,
        InlineCode,
        Emphasis,
    )


def streaming() -> tuple[RuleSpec, ...]:
    """Create the streaming-compatible rule preset."""
    return (
        Table(require_body_pipe=False),
        ThematicBreak,
        FencedCode,
        IndentedCode,
        HtmlBlock,
        List,
        AtxHeading,
        SetextHeading,
        Blockquote,
        HardBreak,
        Autolink,
        RawHtml,
        BackslashEscape,
        CharacterReference,
        Image(references=False),
        Link(references=False),
        InlineCode,
        Strikethrough,
        Emphasis,
    )


def github() -> tuple[RuleSpec, ...]:
    """Create the GitHub-flavored Markdown rule preset."""
    return (
        Table(require_body_pipe=False),
        ThematicBreak,
        FencedCode,
        IndentedCode,
        HtmlBlock(disallowed_tags=GFM_DISALLOWED_HTML_TAGS),
        List(task=True),
        AtxHeading,
        SetextHeading,
        Blockquote,
        HardBreak,
        Autolink,
        RawHtml(disallowed_tags=GFM_DISALLOWED_HTML_TAGS, comment_style='gfm'),
        BackslashEscape,
        CharacterReference,
        Footnote,
        Image,
        Link,
        InlineCode,
        Strikethrough,
        Emphasis,
        ExtendedAutolink,
    )


def _resolve_builtin_preset(value: Iterable[RuleSpec] | PresetFactory, /, *, stacklevel: int) -> Iterable[RuleSpec]:
    factory: PresetFactory | None = None
    if value is commonmark:
        factory = commonmark
    elif value is github:
        factory = github
    elif value is streaming:
        factory = streaming

    if factory is None:
        return cast(Iterable[RuleSpec], value)

    warnings.warn(
        f'Passing {factory.__name__} without calling it is deprecated and will be removed in 1.0; '
        f'use {factory.__name__}() instead.',
        DeprecationWarning,
        stacklevel=stacklevel,
    )
    return factory()


def create_preset(
    base: Iterable[RuleSpec] | PresetFactory,
    *,
    prepend: Iterable[RuleSpec] = (),
    remove: Iterable[RuleSpec] = (),
    replace: Iterable[RuleSpec] = (),
    append: Iterable[RuleSpec] = (),
) -> list[RuleSpec]:
    """Create a derived preset from an existing rule list.

    Rules are matched by their stable ``name``. Replacement rules keep the
    position of the rule they replace. Use ``append`` for rules that are not
    present in the base preset. Passing a built-in preset function without
    calling it is deprecated; pass the result of ``commonmark()``, ``github()``,
    or ``streaming()`` instead.
    """
    base = _resolve_builtin_preset(base, stacklevel=3)

    remove_names = {rule.name for rule in remove}
    replacements = _replacement_map(replace)
    replaced: set[str] = set()

    rules = list(prepend)
    for rule in base:
        name = rule.name
        if name in remove_names:
            continue
        replacement = replacements.get(name)
        if replacement is not None:
            rules.append(replacement)
            replaced.add(name)
            continue
        rules.append(rule)

    missing = sorted(set(replacements) - replaced)
    if missing:
        names = ', '.join(missing)
        raise ValueError(f'cannot replace rules that are not in the base preset: {names}')

    rules.extend(append)
    return rules


def _replacement_map(rules: Iterable[RuleSpec]) -> dict[str, RuleSpec]:
    replacements: dict[str, RuleSpec] = {}
    for rule in rules:
        name = rule.name
        if name in replacements:
            raise ValueError(f'duplicate replacement rule: {name}')
        replacements[name] = rule
    return replacements
