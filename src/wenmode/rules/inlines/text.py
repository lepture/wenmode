from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from wenmode.nodes import Break, Node, Text
from wenmode.rules.base import InlineRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Wenmode


ESCAPABLE = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'
NUMERIC_CHARACTER_REFERENCE_RE = re.compile(r'&#(?P<base>[xX]?)(?P<digits>[0-9A-Fa-f]+);')


class BackslashEscape(InlineRule):
    def __init__(self) -> None:
        super().__init__('backslash_escape', rf'\\(?=[{ESCAPABLE}])', '\\')

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Text(value=text[match.end()], _parse_emphasis=False), match.end() + 1


class CharacterReference(InlineRule):
    def __init__(self) -> None:
        super().__init__('character_reference', r'&(?:#[xX][0-9A-Fa-f]+|#[0-9]+|[A-Za-z][A-Za-z0-9]{1,31});', '&')

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        value = match.group(0)
        numeric = NUMERIC_CHARACTER_REFERENCE_RE.match(value)
        if numeric is not None:
            base = 16 if numeric.group('base') else 10
            codepoint = int(numeric.group('digits'), base)
            if codepoint == 0:
                return Text(value='\ufffd', _parse_emphasis=False), match.end()
            if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
                return Text(value=value, _parse_emphasis=False), match.end()
        return Text(value=html.unescape(value), _parse_emphasis=False), match.end()


class HardBreak(InlineRule):
    def __init__(self) -> None:
        super().__init__('hard_break', r'(?:\\| {2,})\r?\n', '\\ ')

    def parse(
        self, parser: Wenmode, text: str, match: re.Match[str], state: BlockState | None = None
    ) -> tuple[Node | None, int]:
        return Break(), match.end()
