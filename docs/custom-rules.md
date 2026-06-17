# Custom rules

Create a custom rule when you want Wenmode to recognize syntax that is not part
of an existing preset.

## Custom inline rule

An inline rule inherits from `InlineRule`, defines a regex pattern, and returns
a node plus the index where parsing should resume.

This example parses `++marked++` as a `Mark` node.

```python
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Mark, Node
from wenmode.rules.base import InlineRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


class PlusMark(InlineRule):
    def __init__(self) -> None:
        super().__init__('plus_mark', r'\+\+', '+')

    def parse(
        self,
        parser: Parser,
        text: str,
        match: re.Match[str],
        state: BlockState | None = None,
    ) -> tuple[Node | None, int]:
        end = text.find('++', match.end())
        if end == -1:
            return None, match.start()

        children = parser.parse_inlines(text[match.end():end], state)
        return Mark(children=children), end + 2
```

Register it like any other rule.

```python
from wenmode import Wenmode
from wenmode.rules import Emphasis

wenmode = Wenmode([PlusMark, Emphasis])

assert wenmode.render('++very *important*++\n') == (
    '<p><mark>very <em>important</em></mark></p>\n'
)
```

Use `trigger_chars` when possible. It lets the parser quickly find candidate
positions instead of running a search across every inline rule for every step.

## Custom block rule

A block rule inherits from `BlockRule`. The constructor passes a rule name and a
block opener pattern. The `parse()` method can consume lines from `BlockState`
and return a node.

```python
import re

from wenmode.nodes import Paragraph
from wenmode.rules.base import BlockRule
from wenmode.state import BlockState


class BangParagraph(BlockRule):
    def __init__(self) -> None:
        super().__init__('bang_paragraph', r'[ \t]{0,3}!')

    def parse(self, parser, state: BlockState, match: re.Match[str]):
        text = state.line.lstrip(' \t!').rstrip('\r\n')
        state.advance()
        return Paragraph(children=parser.parse_inlines(text, state))
```

The parser expects a block rule to advance the state when it consumes input. If
the rule decides not to handle a match, return `None`.

## Custom continuation rule

A continuation rule inherits from `ContinueRule` and implements
`parse_paragraph_continuation()`. It receives the paragraph lines collected so
far and may return a replacement node.

Setext headings are implemented this way: the parser starts reading a paragraph,
then a following underline line turns that paragraph into a heading.

## Rule options

Use configured rule instances when your rule has options.

```python
from wenmode import Parser
from wenmode.rules import Image, Link

parser = Parser([
    Link(references=False),
    Image(references=False),
])
```

Wenmode stores enabled rules by `name`, so registering another instance with the
same name replaces the previous configuration.

## Extension state

Parser, rule, and transform instances should not store per-parse mutable state.
Use `BlockState.store` with a `StateKey` when a rule or transform needs shared
state for one parse.

```python
from __future__ import annotations

import re

from wenmode.nodes import Node, Root
from wenmode.rules.base import BlockRule, Rule
from wenmode.state import BlockState, StateKey

TERMS = StateKey('my_package.terms', lambda: {})
TERM_RE = re.compile(r'^[ \t]{0,3}@term\[(?P<label>[^\]]+)]:[ \t]*(?P<title>.*)$')


class Glossary(Rule):
    def __init__(self) -> None:
        super().__init__('glossary')
        self.root_transforms = [GlossaryTransform()]


class TermDefinition(BlockRule):
    def __init__(self) -> None:
        super().__init__('term_definition', r'[ \t]{0,3}@term\[')

    def parse(self, parser, state: BlockState, match: re.Match[str]) -> Node | None:
        term = TERM_RE.match(state.line.rstrip('\r\n'))
        if term is None:
            return None

        state.store.get(TERMS)[term.group('label')] = term.group('title')
        state.advance()
        return None


class GlossaryTransform:
    name = 'glossary'
    defer_inlines = False
    required_rules = [TermDefinition]

    def prepare(self, parser, root: Root, state: BlockState) -> None:
        pass

    def transform(self, parser, root: Root, state: BlockState) -> None:
        root.data = {'terms': dict(state.store.get(TERMS))}
```

`RootTransform.required_rules` are registered automatically. Nested block
parsing shares the same store, while each top-level parse gets a fresh store.

## Testing a rule

Test custom rules at the parser and renderer boundary. A small rule usually
needs three cases:

- recognized syntax renders as expected,
- unmatched or incomplete syntax stays as text,
- nested inline parsing works if the rule calls `parser.parse_inlines()`.

```python
from wenmode import HTMLRenderer, Parser
from wenmode.rules import Emphasis


def render(markdown: str) -> str:
    parser = Parser([PlusMark, Emphasis])
    return HTMLRenderer().render(parser.parse(markdown))


def test_plus_mark() -> None:
    assert render('++a *b*++\n') == '<p><mark>a <em>b</em></mark></p>\n'
    assert render('++open\n') == '<p>++open</p>\n'
```
