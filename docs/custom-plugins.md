(custom-plugins)=
# Custom Plugins

```{rst-class} lead
Create plugins for `Wenmode(..., plugins=[...])` that package syntax rules,
nodes, renderer handlers, and setup options.
```

---

Create a plugin when you want to add syntax or output behavior that is not part
of the CommonMark, GFM, mdast directive, or built-in plugin surface. A plugin is
the unit your application installs with `Wenmode(..., plugins=[plugin])`.

Before writing a custom plugin, check whether the feature can be expressed as:

- a preset or configured rule list, when no new node type is needed,
- a built-in plugin from {ref}`plugins`, when Wenmode already provides the
  syntax,
- a directive renderer, when the syntax should stay in the mdast directive
  family.

Plugins usually keep these pieces together:

- custom node classes,
- parser rules and root transforms,
- renderer handlers for supported output formats,
- a `setup(wenmode, **options)` function.

## Plugin Shape

A plugin can be a module or an object. During construction, `Wenmode` looks for
a callable `setup()` function on each plugin in `plugins=[...]` and passes the
`Wenmode` instance. Use `Wenmode.use(plugin, **options)` when a plugin needs
setup options.

```python
from typing import Any

from wenmode import Wenmode
from wenmode.rules import Emphasis


class EmphasisOnlyPlugin:
    def setup(self, wenmode: Wenmode, **options: Any) -> None:
        wenmode.register_rule(Emphasis)


wen = Wenmode([], plugins=[EmphasisOnlyPlugin()])

assert wen.render('*emphasis*') == '<p><em>emphasis</em></p>\n'
```

Module plugins use the same shape. This is the pattern used by built-in plugins:

```{code-block} python
:caption: my_project/wenmode_plugins/plus_mark.py

from typing import Any

from wenmode import Wenmode


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules(rules)
    wenmode.register_renderer_handlers(handlers)
```

Applications import the module and pass it to `plugins`:

```{code-block} python
from wenmode import Wenmode
from my_project.wenmode_plugins import plus_mark

wen = Wenmode(plugins=[plus_mark])
```

## Complete Inline Plugin

This plugin parses `++marked++` into a custom `plusMark` node and teaches the
HTML renderer how to serialize it.

```python
import re
from typing import Any

from wenmode import HTMLRenderer, Wenmode
from wenmode.nodes import Node, Parent
from wenmode.parser import Parser
from wenmode.renderers import RenderContext
from wenmode.rules import InlineRule, Rule
from wenmode.state import BlockState


class PlusMarkNode(Parent):
    type = 'plusMark'

    def __init__(self, children: list[Node]) -> None:
        super().__init__(self.type, children=children)


class PlusMarkRule(InlineRule):
    name = 'plus_mark'
    pattern = r'\+\+'
    trigger_chars = '+'

    def parse(
        self,
        parser: Parser,
        text: str,
        match: re.Match[str],
        state: BlockState,
    ) -> tuple[Node | None, int]:
        end = text.find('++', match.end())
        if end == -1:
            return None, match.start()

        value_start = match.end()
        children = parser.parse_inlines(
            text[value_start:end],
            state,
            source=parser.inline_source(text, state, value_start, end),
        )
        return PlusMarkNode(children=children), end + 2


def render_plus_mark(renderer: HTMLRenderer, node: PlusMarkNode, context: RenderContext) -> str:
    return f'<mark>{renderer.render_children(node.children, context)}</mark>'


nodes = {PlusMarkNode.type: PlusMarkNode}
rules: list[type[Rule] | Rule] = [PlusMarkRule]
handlers = {'html': {PlusMarkNode.type: render_plus_mark}}


class PlusMarkPlugin:
    def setup(self, wenmode: Wenmode, **options: Any) -> None:
        wenmode.register_rules(rules)
        wenmode.register_renderer_handlers(handlers)


wen = Wenmode(plugins=[PlusMarkPlugin()])
expected = '''
<p><mark>very <em>important</em></mark></p>
'''

assert wen.render('++very *important*++') == expected.lstrip()
```

The parser creates the node. Renderer handlers decide how each output format
serializes that node. If a renderer has no handler for a node type,
`BaseRenderer` falls back to rendering child nodes or a literal `value`.
The `nodes` mapping is optional for rendering, but expose it when callers may
restore serialized AST data with `wenmode.ast.from_ast()`.

## Renderer Handlers

`register_renderer_handlers()` accepts a mapping keyed by renderer name. Only
handlers for the current renderer are installed.

```{code-block} python
handlers = {
    'html': {'plusMark': render_plus_mark_html},
    'markdown': {'plusMark': render_plus_mark_markdown},
    'rst': {'plusMark': render_plus_mark_rst},
}


def setup(wenmode: Wenmode, **options: Any) -> None:
    wenmode.register_rules([PlusMarkRule])
    wenmode.register_renderer_handlers(handlers)
```

Use stable node `type` values. Renderer handlers are selected by `node.type`,
not by the Python class name.

When a plugin needs to add document-level output before or after the rendered
root, prefer renderer root hooks over replacing the `root` handler. Use
the pseudo handler names `root:pre` and `root:post` for prefixes such as
metadata blocks and suffixes. This keeps the renderer's built-in root behavior,
such as footnote sections or deferred image definitions, intact.

```{code-block} python
handlers = {
    'markdown': {'root:pre': render_document_metadata},
}
```

## Setup Options

Expose options on `setup()` when callers need to enable part of a plugin. This
is how built-in plugins such as `math` and `spoiler` let callers install only
their inline or block syntax.

```{code-block} python
def setup(wenmode: Wenmode, inline: bool = True, block: bool = True, **options: Any) -> None:
    selected_rules = []
    if inline:
        selected_rules.append(MyInlineRule)
    if block:
        selected_rules.append(MyBlockRule)

    wenmode.register_rules(selected_rules)
    wenmode.register_renderer_handlers(handlers)
```

Unknown options are accepted by convention so plugins can share a consistent
`setup(wenmode, **options)` shape. Validate option values inside `setup()` when
the plugin needs stricter behavior.

## Rule Types Inside Plugins

Rules are implementation details of a plugin. Use the rule type that matches
the syntax you are adding:

| Rule type | Use it for |
| --- | --- |
| `InlineRule` | inline spans such as `++marked++` |
| `BlockRule` | standalone block starts such as fenced blocks |
| `ContinueRule` | paragraph continuations such as definition-list items |
| `Rule` with root transforms | document-wide state or tree rewrites |

Every rule has a stable `name`. Parser rule names are used as dictionary keys,
and block rule names are used as regex group names when the parser compiles
block openers, so use snake_case identifier-style names.

Rules also have an `order` class attribute. Block and inline rules default to
`order = 100`; lower values run earlier when syntax overlaps.

```{code-block} python
class MyRule(InlineRule):
    name = 'my_rule'
    pattern = r'!!'
    trigger_chars = '!'
    order = 90
```

`Wenmode.register_rule()` and `Wenmode.register_rules()` accept rule classes or
configured rule instances. Classes are instantiated automatically. Instances are
useful when the rule itself has options.

For stateless custom rules, prefer defining `name`, `pattern`, and
`trigger_chars` as class attributes. Keep `__init__()` only when the rule needs
caller-provided configuration.

## Parsing Nested Content

When a rule contains nested Markdown content, call parser helpers so the nested
content uses the same rule set and, when enabled, the same source-position
behavior.

Inline rules should pass the source range of the nested label or body:

```{code-block} python
value_start = match.end()
value_end = text.find('++', value_start)

children = parser.parse_inlines(
    text[value_start:value_end],
    state,
    source=parser.inline_source(text, state, value_start, value_end),
)
```

Block rules should collect the original source for generated nested text before
calling `parser.parse_blocks()`:

```{code-block} python
source = state.source.collect()
for line in lines:
    source.add(state.index, 0, line)
    state.advance()

children = parser.parse_blocks(
    ''.join(lines),
    parent_state=state,
    source=source.map(),
)
```

If a rule decides not to handle a match, return `None` without consuming input.
For inline rules, return `(None, match.start())`. The parser will continue with
the normal fallback behavior.

## Source Positions

Most rules should not set the outer node position. If `positions=True` and the
returned node has `position=None`, the parser fills it with the complete source
range consumed by the rule. Positions store 0-based offsets. If a rule sets a
position itself, the parser will not overwrite it.

For a simple inline rule, this is enough:

```{code-block} python
from dataclasses import dataclass

from wenmode.nodes import Node


@dataclass
class MentionNode(Node):
    name: str = ''
    type: str = 'mention'


class MentionRule(InlineRule):
    name = 'mention'
    pattern = r'@[A-Za-z][A-Za-z0-9_]*'
    trigger_chars = '@'

    def parse(
        self,
        parser: Parser,
        text: str,
        match: re.Match[str],
        state: BlockState,
    ) -> tuple[Node | None, int]:
        return MentionNode(name=match.group(0)[1:]), match.end()
```

The parser will assign `MentionNode.position` to the `@name` span. Do not set it
manually unless the node should point somewhere else.

Set positions manually only when a node or child node should point to a smaller
range than the complete syntax. This usually happens when a transform splits an
existing text node:

```{code-block} python
from wenmode.nodes import Position, Text

if node.position is not None:
    child = Text(
        value=node.value[start:end],
        position=Position(
            start=node.position.start + start,
            end=node.position.start + end,
        ),
    )
```

For nested Markdown, prefer passing a source map instead of setting every child
manually. In the `++marked++` example above, `parser.inline_source()` maps
children to `marked`, while the returned `PlusMarkNode` still gets the full
`++marked++` range from the parser.

`Root.to_ast()` converts offsets to unist-style `line` and `column` fields.
Standalone nodes, including nodes yielded by `Parser.parse_iter()`, do not have
root line-start context and serialize positions with offsets only.

## Plugin State And Transforms

Parser, rule, plugin, and transform instances should not store per-parse
mutable state. Use `BlockState.store` with a `StateKey` when a plugin needs
shared state for one parse.

```{code-block} python
from wenmode.state import StateKey

TERMS = StateKey('my_package.terms', lambda: {})
```

Root transforms can declare `required_rules`; the parser automatically
registers missing required rules when it rebuilds the rule set.

Use `defer_inlines = True` only when inline parsing needs document-wide state
collected by a transform, such as reference-style links or abbreviation
definitions. Rule sets with deferred inline parsing cannot be used with
streaming output.

If a plugin is intended for streaming output, test it through
`Wenmode(streaming, plugins=[plugin]).stream(...)` or through an equivalent
custom streaming rule list.

## Testing Plugins

Test the plugin through `Wenmode(..., plugins=[...])`, because that is the
recommended API applications will call.

```{code-block} python
from wenmode import HTMLRenderer, Wenmode


def render(markdown: str) -> str:
    return Wenmode(renderer=HTMLRenderer(), plugins=[PlusMarkPlugin()]).render(markdown)


def test_plus_mark() -> None:
    assert render('++a *b*++') == '<p><mark>a <em>b</em></mark></p>\n'
    assert render('++open') == '<p>++open</p>\n'
```

Useful cases include:

- recognized syntax renders as expected,
- unmatched or incomplete syntax stays as text,
- nested inline or block parsing works,
- renderer handlers are registered for each supported output format,
- setup options change behavior as documented,
- per-parse state does not leak between renders.
