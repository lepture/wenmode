from __future__ import annotations

import html
import re
from typing import TYPE_CHECKING

from wenmode.nodes import Break, Node, Text

from ..._parser.state import BlockState
from ..base import InlineRule

if TYPE_CHECKING:
    from wenmode.parser import Parser


ESCAPABLE = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'
ESCAPABLE_CHARS = '!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~'
NUMERIC_CHARACTER_REFERENCE_RE = re.compile(r'&#(?P<base>[xX]?)(?P<digits>[0-9A-Fa-f]+);')


class BackslashEscape(InlineRule):
    """Parse backslash escapes for Markdown punctuation.

    Markdown syntax:

    .. code-block:: markdown

       \\*
    """

    name = 'backslash_escape'
    pattern = rf'\\(?=[{ESCAPABLE}])'
    trigger_chars = '\\'

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        if start + 1 >= len(text) or text[start] != '\\' or text[start + 1] not in ESCAPABLE_CHARS:
            return None, start
        return Text(value=text[start + 1], _parse_emphasis=False), start + 2


class CharacterReference(InlineRule):
    """Parse named and numeric character references.

    Markdown syntax:

    .. code-block:: markdown

       &copy;
    """

    name = 'character_reference'
    pattern = r'&(?:#[xX][0-9A-Fa-f]+|#[0-9]+|[A-Za-z][A-Za-z0-9]{1,31});'
    trigger_chars = '&'

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        match = self.compiled.match(text, start)
        if match is None:
            return None, start
        value = match.group(0)
        numeric = NUMERIC_CHARACTER_REFERENCE_RE.match(value)
        if numeric is not None:
            if numeric.group('base'):
                base = 16
            else:
                base = 10
            codepoint = int(numeric.group('digits'), base)
            if codepoint == 0:
                return Text(value='\ufffd', _parse_emphasis=False), match.end()
            if codepoint > 0x10FFFF or 0xD800 <= codepoint <= 0xDFFF:
                return Text(value=value, _parse_emphasis=False), match.end()
        return Text(value=html.unescape(value), _parse_emphasis=False), match.end()


class HardBreak(InlineRule):
    """Parse hard line breaks created with backslash or trailing spaces.

    Markdown syntax:

    .. code-block:: markdown

       line\\
       break
    """

    name = 'hard_break'
    pattern = r'(?:\\| {2,})\r?\n'

    def search(self, text: str, pos: int = 0) -> int | None:
        return find_hard_break(text, pos)

    def parse(self, parser: Parser, text: str, start: int, state: BlockState) -> tuple[Node | None, int]:
        match = self.compiled.match(text, start)
        if match is None:
            return None, start
        return Break(), match.end()


def find_hard_break(text: str, pos: int) -> int | None:
    newline = text.find('\n', pos)
    while newline != -1:
        if newline > 0 and text[newline - 1] == '\r':
            line_end = newline - 1
        else:
            line_end = newline
        if line_end > 0 and text[line_end - 1] == '\\' and line_end - 1 >= pos:
            return line_end - 1

        space_start = line_end
        while space_start > 0 and text[space_start - 1] == ' ':
            space_start -= 1
        start = max(space_start, pos)
        if line_end - start >= 2:
            return start

        newline = text.find('\n', newline + 1)
    return None
