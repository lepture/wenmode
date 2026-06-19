(custom-rules)=
# Custom rules

```{rst-class} lead
Create custom inline, block, continuation, and transform rules for new Markdown
syntax.
```

---

Create a custom rule when you want Wenmode to recognize syntax that is not part
of an existing preset. Custom rules use the same base classes as built-in rules:
`InlineRule`, `BlockRule`, `ContinueRule`, and plain `Rule` for extensions that
only provide root transforms.

## Rule API

Every rule has a stable `name`. Parser rule names are used as dictionary keys
in `parser.rules`, and block rule names are also used as regex group names when
the parser compiles block openers, so use snake_case identifier-style names.

Rules also have an `order` class attribute. Block and inline rules default to
`order = 100`; lower values run earlier when syntax overlaps.

```python
class MyRule(InlineRule):
    order = 90
```

`Parser` and `Wenmode` accept either rule classes or configured rule instances.
Classes are instantiated automatically. Instances are useful for rules with
options.

## Custom inline rule

An inline rule inherits from `InlineRule`, defines a regex pattern, and returns
a node plus the index where parsing should resume.

This example parses `++marked++` as a `Mark` node.

The target Markdown syntax is:

```markdown
This is ++marked++ text.
```

```python
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Mark as MarkNode
from wenmode.nodes import Node
from wenmode.rules import InlineRule
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

        value_start = match.end()
        children = parser.parse_inlines(
            text[value_start:end],
            state,
            source=parser.inline_source(text, value_start, end),
        )
        return MarkNode(children=children), end + 2
```

Register it like any other rule.

```python
from wenmode import Wenmode
from wenmode.rules import Emphasis

wenmode = Wenmode([PlusMark, Emphasis])
text = '++very *important*++'
expected = '''
<p><mark>very <em>important</em></mark></p>
'''

assert wenmode.render(text) == expected.lstrip()
```

The third `InlineRule` constructor argument is `trigger_chars`. Use it when a
rule starts with known literal characters. The parser then jumps directly to
those characters and calls `rule.compiled.match()` there. If `trigger_chars` is
empty, the parser calls `rule.search(text, pos)`; override `search()` for rules
that need custom scanning behavior.

If an inline rule decides not to handle a match, return
`(None, match.start())`. The parser will emit the marker as text and continue.

When source positions are enabled, the parser assigns a position to the node
returned by the inline rule. If the rule recursively parses child inline
content, pass `source=parser.inline_source(text, start, end)` so child nodes map
back to the matching slice of the original inline source.

## Custom node and renderers

Use a custom node when your syntax does not map to one of Wenmode's built-in
node types. The parser only creates the node; each renderer still needs to know
how to serialize it.

This example parses reStructuredText keyboard roles such as
`` :kbd:`Ctrl+C` ``. Markdown has no native keyboard-input node, so the example
creates a `KeyboardInput` node and registers renderers for HTML, Markdown, and
reStructuredText output.

```python
import re

from wenmode import HTMLRenderer, MarkdownRenderer, Parser, RSTRenderer
from wenmode.nodes import Literal, Node
from wenmode.renderers import RenderContext
from wenmode.rules import InlineRule
from wenmode.state import BlockState


class KeyboardInput(Literal):
    def __init__(self, value: str) -> None:
        super().__init__(type='keyboardInput', value=value)


class KeyboardInputRole(InlineRule):
    def __init__(self) -> None:
        super().__init__('keyboard_input_role', r':kbd:`', ':')

    def parse(
        self,
        parser: Parser,
        text: str,
        match: re.Match[str],
        state: BlockState | None = None,
    ) -> tuple[Node | None, int]:
        end = text.find('`', match.end())
        if end == -1:
            return None, match.start()

        return KeyboardInput(value=text[match.end() : end]), end + 1


@HTMLRenderer.register('keyboardInput')
def render_keyboard_input_html(
    renderer: HTMLRenderer,
    node: KeyboardInput,
    context: RenderContext,
) -> str:
    return f'<kbd>{renderer.escape_html(node.value)}</kbd>'


@MarkdownRenderer.register('keyboardInput')
def render_keyboard_input_markdown(
    renderer: MarkdownRenderer,
    node: KeyboardInput,
    context: RenderContext,
) -> str:
    return f'<kbd>{renderer.escape_text(node.value)}</kbd>'


@RSTRenderer.register('keyboardInput')
def render_keyboard_input_rst(
    renderer: RSTRenderer,
    node: KeyboardInput,
    context: RenderContext,
) -> str:
    return f':kbd:`{renderer.escape_inline_literal(node.value)}`'


parser = Parser([KeyboardInputRole])
root = parser.parse('Press :kbd:`Ctrl+C`.')
expected_html = '''
<p>Press <kbd>Ctrl+C</kbd>.</p>
'''
expected_markdown = r'''
Press <kbd>Ctrl\+C</kbd>\.
'''
expected_rst = '''
Press :kbd:`Ctrl+C`.
'''

assert root.to_ast() == {
    'type': 'root',
    'children': [
        {
            'type': 'paragraph',
            'children': [
                {'type': 'text', 'value': 'Press '},
                {'type': 'keyboardInput', 'value': 'Ctrl+C'},
                {'type': 'text', 'value': '.'},
            ],
        }
    ],
}
assert HTMLRenderer().render(root) == expected_html.lstrip()
assert MarkdownRenderer().render(root) == expected_markdown.lstrip()
assert RSTRenderer().render(root) == expected_rst.lstrip()
```

Registering a handler mutates the renderer class, so do it during application
startup or in the module that defines the extension. Without a registered
handler, `BaseRenderer` falls back to rendering `children` or `value`; that may
be useful for plain-text fallbacks, but it will not preserve your custom output
format semantics.

## Custom block rule

A block rule inherits from `BlockRule`. The constructor passes a rule name and a
block opener pattern. The parser wraps each block opener as a named regex group,
matches the current line, and calls the matched rule's `parse()` method.

The `parse()` method receives the parser, the current `BlockState`, and the
matched opener. It must advance `state` when it consumes input.

This example treats a line that starts with `!` as a paragraph after removing
the marker:

```markdown
! Pay attention to *this*.
```

```python
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node, Paragraph
from wenmode.rules import BlockRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


class BangParagraph(BlockRule):
    def __init__(self) -> None:
        super().__init__('bang_paragraph', r'[ \t]{0,3}!')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        marker_end = state.line.find('!') + 1
        text = state.line[marker_end:].strip()
        source = parser.source_map_for_text(
            text,
            state.point_at_line_offset(state.index, state.line.find(text)),
        )
        state.advance()
        return Paragraph(children=parser.parse_inlines(text, state, source=source))
```

If the rule decides not to handle a matched opener, return `None` without
advancing. The parser will fall back to paragraph parsing for that line.

Use `parser.parse_blocks(text, parent_state=state)` when your block rule
contains nested Markdown content. Nested parsing shares the same state store and
increments `state.depth`.

For nested block content with source positions, collect `(text, point)` parts
from the consumed source and pass
`source=parser.source_map_from_parts(parts)` to `parse_blocks()`. The parser
will use that source map for nested block and inline nodes.

## Custom continuation rule

A continuation rule inherits from `ContinueRule` and implements
`parse_paragraph_continuation()`. It receives the paragraph lines collected so
far and may return a replacement node. Setext headings and definition lists are
implemented this way.

This example turns a paragraph followed by a line of `!` markers into a level 6
heading:

```markdown
Important title
!!!
```

```python
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Heading, Node
from wenmode.rules import ContinueRule
from wenmode.state import BlockState

if TYPE_CHECKING:
    from wenmode.parser import Parser


BANG_HEADING_RE = re.compile(r'[ \t]{0,3}!+[ \t]*$')


class BangHeading(ContinueRule):
    def __init__(self) -> None:
        super().__init__('bang_heading')

    def matches(self, line: str) -> bool:
        return line.lstrip(' \t').startswith('!')

    def parse_paragraph_continuation(
        self,
        parser: Parser,
        state: BlockState,
        lines: list[str],
    ) -> Node | None:
        if BANG_HEADING_RE.match(state.line) is None:
            return None

        state.advance()
        text = ''.join(lines).strip()
        return Heading(depth=6, children=parser.parse_inlines(text, state))
```

`matches()` is optional, but it is useful as a cheap pre-check before doing more
expensive parsing.

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

```python
parser.register_rule(Link(references=False))
```

Root transforms can declare `required_rules`; the parser automatically
registers missing required rules when it rebuilds the rule set.

## Extension state and transforms

Parser, rule, and transform instances should not store per-parse mutable state.
Use `BlockState.store` with a `StateKey` when a rule or transform needs shared
state for one parse.

This example collects glossary term definitions from block syntax and stores the
result on the root node:

```markdown
@term[HTML]: HyperText Markup Language
@term[AST]: Abstract Syntax Tree
```

```python
from __future__ import annotations

import re
from typing import TYPE_CHECKING

from wenmode.nodes import Node, Root
from wenmode.rules import BlockRule, RootTransform, Rule
from wenmode.state import BlockState, StateKey

if TYPE_CHECKING:
    from wenmode.parser import Parser


TERMS = StateKey('my_package.terms', lambda: {})
TERM_RE = re.compile(r'^[ \t]{0,3}@term\[(?P<label>[^\]]+)]:[ \t]*(?P<title>.*)$')


class Glossary(Rule):
    def __init__(self) -> None:
        super().__init__('glossary')
        self.root_transforms: list[RootTransform] = [GlossaryTransform()]


class TermDefinition(BlockRule):
    def __init__(self) -> None:
        super().__init__('term_definition', r'[ \t]{0,3}@term\[')

    def parse(self, parser: Parser, state: BlockState, match: re.Match[str]) -> Node | None:
        term = TERM_RE.match(state.line.rstrip('\r\n'))
        if term is None:
            return None

        state.store.get(TERMS)[term.group('label')] = term.group('title')
        state.advance()
        return None


class GlossaryTransform(RootTransform):
    name = 'glossary'
    required_rules = [TermDefinition]

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        root.data = {'terms': dict(state.store.get(TERMS))}
```

`StateKey.factory` creates the value the first time it is requested for a parse.
Each top-level parse gets a fresh store. Nested block parsing shares the same
store, so definitions inside block quotes, lists, directives, or footnotes are
visible to document-level transforms.

Root transforms inherit from the `RootTransform` base class. The base provides
no-op `prepare()` and `transform()` methods plus default `defer_inlines` and
`required_rules` values, so subclasses only need to override the parts they use.
A transform must set:

- `name`, used for deduplication when multiple rules attach the same transform.

Subclasses can also configure:

- `required_rules`, when it needs rule classes or configured rule instances to
  auto-register.
- `defer_inlines = True`, when inline parsing must wait until after
  `prepare()`.
- `prepare(parser, root, state)`, when it needs to run after block parsing.
- `transform(parser, root, state)`, when it needs to run after deferred inline parsing is
  resolved.

Set `defer_inlines = True` only when inline rules need document-wide state
collected by `prepare()`, such as reference-style links. Rule sets with deferred
inlines cannot be used with streaming output.

## Testing a rule

Test custom rules at the parser and renderer boundary. A small rule usually
needs these cases:

- recognized syntax renders as expected,
- unmatched or incomplete syntax stays as text,
- nested inline parsing works if the rule calls `parser.parse_inlines()`,
- custom node renderers are registered for each output format you support,
- any rule option changes the enabled behavior,
- per-parse state does not leak between parser calls.

```python
from wenmode import HTMLRenderer, Parser
from wenmode.rules import Emphasis


def render(markdown: str) -> str:
    parser = Parser([PlusMark, Emphasis])
    return HTMLRenderer().render(parser.parse(markdown))


EXPECTED_MARKED = '''
<p><mark>a <em>b</em></mark></p>
'''
EXPECTED_OPEN = '''
<p>++open</p>
'''


def test_plus_mark() -> None:
    marked = '++a *b*++'
    open_marker = '++open'

    assert render(marked) == EXPECTED_MARKED.lstrip()
    assert render(open_marker) == EXPECTED_OPEN.lstrip()
```
