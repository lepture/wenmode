from __future__ import annotations

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
    SetextHeading,
    Strikethrough,
    Table,
    ThematicBreak,
)
from .rules.base import Rule

RuleSpec = type[Rule] | Rule

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

commonmark: tuple[RuleSpec, ...] = (
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

streaming: tuple[RuleSpec, ...] = (
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

github: tuple[RuleSpec, ...] = (
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


def create_preset(
    base: Iterable[RuleSpec],
    *,
    prepend: Iterable[RuleSpec] = (),
    remove: Iterable[RuleSpec] = (),
    replace: Iterable[RuleSpec] = (),
    append: Iterable[RuleSpec] = (),
) -> list[RuleSpec]:
    """Create a derived preset from an existing rule list.

    Rules are matched by their stable ``name``. Replacement rules keep the
    position of the rule they replace. Use ``append`` for rules that are not
    present in the base preset.
    """
    remove_names = {_rule_name(rule) for rule in remove}
    replacements = _replacement_map(replace)
    replaced: set[str] = set()

    rules = list(prepend)
    for rule in base:
        name = _rule_name(rule)
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
        name = _rule_name(rule)
        if name in replacements:
            raise ValueError(f'duplicate replacement rule: {name}')
        replacements[name] = rule
    return replacements


def _rule_name(rule: RuleSpec) -> str:
    if isinstance(rule, Rule):
        return rule.name
    name = getattr(rule, 'name', None)
    if isinstance(name, str):
        return name
    return cast(Callable[[], Rule], rule)().name
