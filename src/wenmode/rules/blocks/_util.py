from typing import TYPE_CHECKING

from ..._parser.rule_base import BlockRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


def starts_nonparagraph_block(parser: "Parser", line: str) -> bool:
    rule_names = {
        'atx_heading',
        'container_directive',
        'fenced_code',
        'fenced_directive',
        'indented_code',
        'leaf_directive',
        'list',
        'thematic_break',
    }
    for name in rule_names:
        rule = parser.rules.get(name)
        if isinstance(rule, BlockRule) and rule.compiled.match(line):
            return True
    return False
