---
description: Create custom Wenmode plugins that package parser rules, node classes, renderer handlers, transforms, setup options, and plugin state.
---

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
- a `setup(wen, /)` function.

## Plugin Shape

A plugin can be a module or an object. During construction, `Wenmode` calls
`setup(wen, /)` on each plugin in `plugins=[...]`. Use `configure()` to return a
configured plugin object when a plugin needs options.

For simple delimiter or fenced-block syntax, import `BlockFenced`,
`InlineDelimited`, or `InlineLiteral` from `wenmode.plugins`. The underlying
implementation remains internal; `wenmode.plugins` is the supported import path
for custom plugins.

```python
from wenmode import Wenmode
from wenmode.rules import Emphasis


class EmphasisOnlyPlugin:
    def setup(self, wen: Wenmode, /) -> None:
        wen.register_rule(Emphasis)


wen = Wenmode([], plugins=[EmphasisOnlyPlugin()])

assert wen.render('*emphasis*') == '<p><em>emphasis</em></p>\n'
```

Module plugins expose `setup()`:

```{code-block} python
:caption: my_project/wenmode_plugins/plus_mark.py

from wenmode import Wenmode


def setup(wen: Wenmode, /) -> None:
    wen.register_rules(rules)
    wen.register_renderer_handlers(handlers)
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
from dataclasses import dataclass

from wenmode import Wenmode
from wenmode.nodes import Parent
from wenmode.rules import InlineCandidate, InlineRule


@dataclass
class PlusMarkNode(Parent):
    type: str = 'plusMark'


class PlusMarkRule(InlineRule):
    name = 'plus_mark'
    opener = '+'

    def parse(self, parser, text, candidate, state):
        start = candidate.start
        if not text.startswith('++', start):
            return None, start
        value_start = start + 2
        close = text.find('++', value_start)
        if close == -1:
            return None, start
        children = parser.parse_inlines(text[value_start:close], state)
        return PlusMarkNode(children=children), close + 2


nodes = [PlusMarkNode]
rules = [PlusMarkRule]
handlers = {
    'html': {
        PlusMarkNode.type: lambda renderer, node, context: (
            f'<mark>{renderer.render_children(node.children, context)}</mark>'
        )
    }
}


class PlusMarkPlugin:
    nodes = nodes
    rules = rules
    handlers = handlers

    def setup(self, wen: Wenmode, /) -> None:
        wen.register_rules(self.rules)
        wen.register_renderer_handlers(self.handlers)


wen = Wenmode(plugins=[PlusMarkPlugin()])
expected = '''
<p><mark>very <em>important</em></mark></p>
'''

assert wen.render('++very *important*++') == expected.lstrip()
```

The custom `InlineRule` creates the parser node. If no renderer handler matches
the node type, `BaseRenderer` falls back to child nodes or a literal `value`.
Expose the `nodes` list when callers may restore serialized AST data with
`wenmode.ast.from_ast()`.

## Renderer Handlers

Plugins can expose renderer handlers separately from parser rules. The mapping
is keyed by renderer name; only handlers for the current renderer are installed.

```{code-block} python
handlers = {
    'html': {'plusMark': render_plus_mark_html},
    'markdown': {'plusMark': render_plus_mark_markdown},
    'rst': {'plusMark': render_plus_mark_rst},
}
```

Call `register_renderer_handlers()` inside `setup()`:

```{code-block} python

def setup(wen: Wenmode, /) -> None:
    wen.register_rules([PlusMarkRule])
    wen.register_renderer_handlers(handlers)
```

Use stable node `type` values. Renderer handlers are selected by `node.type`,
not by the Python class name.

For document-level prefixes or suffixes, prefer the `root:pre` and `root:post`
pseudo handlers over replacing the `root` handler. They preserve built-in root
behavior such as footnotes or deferred image definitions.

Root hooks require a complete parsed `Root`, so registering one blocks
`Wenmode.stream()`. Plugins that need incremental output should avoid root
hooks until a streaming hook API exists.

```{code-block} python
handlers = {
    'markdown': {'root:pre': render_document_metadata},
}
```

## Setup Options

Expose a `configure()` helper when callers need to configure part of a plugin.

```{code-block} python
from dataclasses import dataclass


@dataclass(frozen=True)
class MyPlugin:
    inline: bool = True
    block: bool = True

    def setup(self, wen: Wenmode, /) -> None:
        selected_rules = []
        if self.inline:
            selected_rules.append(MyInlineRule)
        if self.block:
            selected_rules.append(MyBlockRule)

        wen.register_rules(selected_rules)
        wen.register_renderer_handlers(handlers)


def configure(*, inline: bool = True, block: bool = True) -> MyPlugin:
    return MyPlugin(inline=inline, block=block)
```

Validate option values inside `configure()` or the configured plugin's
`setup()` when the plugin needs stricter behavior.

For built-in-style configurable plugins, keep options keyword-only, return an
immutable `@dataclass(frozen=True)` plugin object from `configure()`, and keep
`setup(wen, /)` free of extra parameters. That keeps module plugins and
configured plugin objects interchangeable in `Wenmode(..., plugins=[...])`.

## Rule Types Inside Plugins

Rules are implementation details of a plugin. Use the rule type that matches
the syntax you are adding:

| Rule type | Use it for |
| --- | --- |
| `InlineRule` | inline spans such as `++marked++` |
| `BlockRule` | standalone block starts such as fenced blocks |
| `ContinueRule` | paragraph continuations such as definition-list items |
| `Rule` with node transforms | local in-place node updates that can run during streaming |
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
    opener = '!'
    order = 90
```

`Wenmode.register_rule()` and `Wenmode.register_rules()` accept rule classes or
configured rule instances. Classes are instantiated automatically. Instances are
useful when the rule itself has options.

For stateless custom rules, prefer defining `name`, `opener`, and, when needed,
`pattern` as class attributes. `opener` is a single-character dispatch hint, or
a tuple of single-character dispatch hints; validate longer delimiters inside
`match_candidate()` or `parse()`. Keep `__init__()` only when the rule needs
caller-provided configuration.

## Parsing Nested Content

When a custom rule contains nested Markdown content, call parser helpers so the
nested content uses the same rule set. Wenmode automatically assigns the outer
node the complete range consumed by the rule.

Parse an inline label or body directly when nested child positions are not
needed:

```{code-block} python
children = parser.parse_inlines(text[value_start:value_end], state)
```

When nested children need positions mapped to the original document, pass the
source range explicitly:

```{code-block} python
value_start = start + 2
value_end = text.find('++', value_start)

children = parser.parse_inlines(
    text[value_start:value_end],
    state,
    source=parser.inline_source(text, state, value_start, value_end),
)
```

Block rules can call `parser.parse_blocks()` directly for normal nested
parsing. When nested children need original source positions, collect a source
map before calling it:

```{code-block} python
source = state.source.collect()


def collect_line(line: str) -> str:
    source.add(state.index, 0, line)
    return line


lines = state.consume_until(is_closer, collect_line)

children = parser.parse_blocks(
    ''.join(lines),
    parent_state=state,
    source=source.map(),
)
```

`parser.parse_blocks()` enforces `Parser.max_container_depth` for nested block
content. At the limit, it returns shallow blank-separated paragraphs that
preserve source text and positions. Do not bypass this helper with a custom
recursive parser.

If a rule decides not to handle a match, return `None` without consuming input.
For inline rules, return `(None, start)`. The parser will continue with the
normal fallback behavior.

When a `BlockRule` or `ContinueRule` returns a node, it must advance `state`
past the accepted input. Returning a node without advancing state raises
`RuntimeError`. A `ContinueRule` that returns `None` must leave `state`
unchanged; a block rule may advance state and return `None` when it consumes
input without producing a node.

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
    opener = '@'

    def parse(
        self,
        parser: Parser,
        text: str,
        candidate: InlineCandidate,
        state: BlockState,
    ) -> tuple[Node | None, int]:
        match = candidate.match
        assert match is not None
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

When nested Markdown children need precise positions, prefer a source map over
manual child positions. `parser.inline_source()` maps child nodes to nested
content while the parent keeps the full consumed range.

`Root.to_ast()` converts offsets to unist-style `line` and `column` fields.
Standalone nodes, including `Parser.parse_iter()` results, serialize positions
with offsets only.

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
definitions. A transform that needs to run after deferred inline parsing should
schedule work with `state.defer_inline_callback()`. Rule sets with deferred
inline parsing cannot be used with streaming output.

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
