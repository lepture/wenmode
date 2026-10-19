from __future__ import annotations

from typing import TYPE_CHECKING

from wenmode.nodes import Break, Node, Text
from wenmode.utils.text import CHARACTER_REFERENCE_RE, decode_character_references

from ..._parser.rule_base import InlineCandidate, InlineRule
from ..._parser.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


ESCAPABLE = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'


class BackslashEscape(InlineRule):
    """Parse backslash escapes for Markdown punctuation.

    Markdown syntax:

    .. code-block:: markdown

       \\*
    """

    name = 'backslash_escape'
    pattern = rf'\\(?=[{ESCAPABLE}])'
    opener = '\\'

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        start = candidate.start
        return Text(value=text[start + 1], _parse_emphasis=False), start + 2


class CharacterReference(InlineRule):
    """Parse named and numeric character references.

    Markdown syntax:

    .. code-block:: markdown

       &copy;
    """

    name = 'character_reference'
    pattern = CHARACTER_REFERENCE_RE.pattern
    opener = '&'

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        match = candidate.match
        assert match is not None
        return Text(value=decode_character_references(match.group(0)), _parse_emphasis=False), match.end()


class HardBreak(InlineRule):
    """Parse hard line breaks created with backslash or trailing spaces.

    Markdown syntax:

    .. code-block:: markdown

       line\\
       break
    """

    name = 'hard_break'
    pattern = r'(?:\\| {2,})\r?\n'

    def search_candidate(self, text: str, pos: int = 0) -> InlineCandidate | None:
        start = find_hard_break(text, pos)
        if start is None:
            return None
        match = self.compiled.match(text, start)
        if match is None:
            return None
        return InlineCandidate(start, match)

    def parse(self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState) -> tuple[Node | None, int]:
        match = candidate.match
        assert match is not None
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
