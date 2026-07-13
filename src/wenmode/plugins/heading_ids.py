from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from wenmode.headings import HeadingIdTransform, Slugger
from wenmode.rules import Rule
from wenmode.rules.transforms import NodeTransform

if TYPE_CHECKING:
    from wenmode import Wenmode


@dataclass(frozen=True)
class HeadingIdsPlugin:
    slugger_factory: type[Slugger] = Slugger

    def setup(self, wen: Wenmode, /) -> None:
        transform = HeadingIdTransform(self.slugger_factory)
        atx_heading = wen.parser.rules.get('atx_heading')
        setext_heading = wen.parser.rules.get('setext_heading')
        if atx_heading:
            append_transform(atx_heading, transform)
        if setext_heading:
            append_transform(setext_heading, transform)


def append_transform(rule: Rule, transform: NodeTransform) -> None:
    if not any(existing.name == transform.name for existing in rule.node_transforms):
        rule.node_transforms.append(transform)


def configure(slugger_factory: type[Slugger] = Slugger) -> HeadingIdsPlugin:
    return HeadingIdsPlugin(slugger_factory)


def setup(wen: Wenmode, /) -> None:
    configure().setup(wen)
