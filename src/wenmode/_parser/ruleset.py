from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar, cast

from wenmode.rules.base import BlockRule, ContinueRule, InlineRule, Rule
from wenmode.rules.transforms import RootTransform

T = TypeVar('T', bound=Rule)


@dataclass(frozen=True, slots=True)
class RuleSet:
    """Compiled parser rule configuration."""

    rules: dict[str, Rule]
    block_rules: list[BlockRule]
    inline_rules: list[InlineRule]
    root_transforms: list[RootTransform]
    paragraph_continuations: list[ContinueRule]
    emphasis_enabled: bool
    defer_inlines: bool
    block_rule_order: dict[str, int]
    inline_rule_order: dict[str, int]
    triggered_inline_rules: dict[str, list[InlineRule]]
    search_inline_rules: list[InlineRule]
    inline_trigger_re: re.Pattern[str] | None
    block_openers: re.Pattern[str] | None

    @classmethod
    def from_rules(cls, registered_rules: list[Rule]) -> RuleSet:
        resolved_rules = list(registered_rules)
        root_transforms = collect_root_transforms(resolved_rules)
        for transform in root_transforms:
            for required in transform.required_rules:
                rule = resolve_rule(required)
                if all(registered.name != rule.name for registered in resolved_rules):
                    resolved_rules.append(rule)

        rules = {rule.name: rule for rule in resolved_rules}
        block_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, BlockRule)])
        inline_rules = sorted_by_order([rule for rule in resolved_rules if isinstance(rule, InlineRule)])
        triggered_inline_rules, search_inline_rules = prepare_inline_dispatch(inline_rules)
        return cls(
            rules=rules,
            block_rules=block_rules,
            inline_rules=inline_rules,
            root_transforms=root_transforms,
            paragraph_continuations=[rule for rule in resolved_rules if isinstance(rule, ContinueRule)],
            emphasis_enabled='emphasis' in rules,
            defer_inlines=any(transform.defer_inlines for transform in root_transforms),
            block_rule_order={rule.name: index for index, rule in enumerate(block_rules)},
            inline_rule_order={rule.name: index for index, rule in enumerate(inline_rules)},
            triggered_inline_rules=triggered_inline_rules,
            search_inline_rules=search_inline_rules,
            inline_trigger_re=compile_inline_trigger_re(triggered_inline_rules),
            block_openers=compile_block_openers(block_rules),
        )


def resolve_rule(rule: type[Rule] | Rule) -> Rule:
    if isinstance(rule, type):
        return cast(Callable[[], Rule], rule)()
    return rule


def sorted_by_order(rules: list[T]) -> list[T]:
    return [rule for _, rule in sorted(enumerate(rules), key=lambda item: (item[1].order, item[0]))]


def collect_root_transforms(rules: list[Rule]) -> list[RootTransform]:
    transforms: list[RootTransform] = []
    seen: set[str] = set()
    for rule in rules:
        for transform in rule.root_transforms:
            if transform.name in seen:
                continue
            seen.add(transform.name)
            transforms.append(transform)
    return transforms


def compile_block_openers(rules: list[BlockRule]) -> re.Pattern[str] | None:
    patterns = [f'(?P<{rule.name}>{rule.pattern})' for rule in rules]
    if patterns:
        return re.compile('|'.join(patterns))
    return None


def prepare_inline_dispatch(rules: list[InlineRule]) -> tuple[dict[str, list[InlineRule]], list[InlineRule]]:
    triggered: dict[str, list[InlineRule]] = {}
    search: list[InlineRule] = []
    for rule in rules:
        if rule.name == 'emphasis':
            continue
        if not rule.trigger_chars:
            search.append(rule)
            continue
        for char in rule.trigger_chars:
            triggered.setdefault(char, []).append(rule)
    return triggered, search


def compile_inline_trigger_re(rules: dict[str, list[InlineRule]]) -> re.Pattern[str] | None:
    if not rules:
        return None
    return re.compile(f'[{re.escape("".join(rules))}]')

