(internals)=
# Internals

```{rst-class} lead
Explore Wenmode's node model, parser flow, rule dispatch, root transforms, state,
and renderer internals.
```

---

Wenmode is organized around a small set of data objects and dispatch points:
AST nodes, parser rules, root transforms, parser state, and renderers.

The AST is mdast-compatible. Core Markdown nodes use mdast-style names and
fields: `root.children`, `paragraph.children`, `heading.depth`, `link.url`,
`link.title`, `image.url`, `image.alt`, `code.lang`, and literal `value`
fields. Extensions use the same data-object style with explicit node types such
as `table`, `footnoteReference`, `math`, `ruby`, and the directive node family.

## AST nodes

Node classes live in `wenmode.nodes`. They are dataclasses that describe parsed
content. Rendering behavior is not stored on the nodes; renderers decide how to
turn nodes into output.

```python
from wenmode import Wenmode

text = '# Hello'

root = Wenmode().parse(text)
print(root.to_ast())
```

`Node.to_ast()` returns a plain dictionary representation, recursively
converting child nodes.

```python
{
    'type': 'root',
    'children': [
        {
            'type': 'heading',
            'children': [{'type': 'text', 'value': 'Hello'}],
            'depth': 1,
        }
    ],
}
```

Nodes follow mdast-style `type` names where possible. Common node groups are:

- Parent nodes, such as `root`, `paragraph`, `heading`, `blockquote`, `list`,
  `listItem`, table nodes, directive nodes, and formatting nodes.
- Literal nodes, such as `text`, `inlineCode`, `code`, `html`, `math`, and
  `inlineMath`.
- Leaf nodes, such as `thematicBreak`, `break`, `image`, and
  `footnoteReference`.

Nodes are pure data objects. They do not carry HTML tag names, HTML attributes,
or other renderer hints. `HTMLRenderer`, `MarkdownRenderer`, and custom
renderers own output behavior.

### Positions

When positions are enabled, `node.position` is a `Position` whose `start` and
`end` fields are 0-based offsets into the original source. The parser keeps
line starts on the `Root`; `Root.to_ast()` uses that context to serialize
positions as unist-style `{line, column, offset}` dictionaries.

Standalone `Node.to_ast()` calls do not have access to root line starts, so they
emit offset-only positions. This includes nodes yielded by `Parser.parse_iter()`.

Rule and plugin code should usually work with offsets directly. Regex match
indices and string slice boundaries can be turned into child positions with
simple offset arithmetic:

```python
from wenmode.nodes import Position, Text

node = Text(value='abc', position=Position(start=10, end=13))
child = Text(value='b')
start = 1
end = 2

child.position = Position(
    start=node.position.start + start,
    end=node.position.start + end,
)

assert child.position == Position(start=11, end=12)
```

## Parser flow

`Parser.parse()` creates a fresh `BlockState`, parses block nodes into a
`Root`, runs root transform preparation, resolves deferred inline parsing, runs
root transforms, and returns the root node.

At a high level:

1. Blank lines are skipped.
2. Block openers are matched against enabled `BlockRule` patterns.
3. If no block rule handles the line, the parser reads a paragraph.
4. Paragraph text is parsed with enabled inline rules.
5. Root transforms finalize document-wide features.

`Parser.parse_iter()` follows the block parser incrementally and yields nodes as
they are parsed. It rejects rule sets that require deferred inline transforms.
Because it does not build a root node, position-aware `parse_iter()` output
keeps offset-only position data unless a caller supplies its own line mapping.

## Rules

All rules inherit from `Rule` and have a stable `name`. Enabled rules are
available as `parser.rules`, a dictionary keyed by rule name.

`BlockRule` instances provide a block opener pattern and a `parse()` method.
They receive the parser, current block state, and the matched opener.

`ContinueRule` instances can inspect paragraph continuation lines. This is used
for syntax where a paragraph can become another block, such as setext headings.

`InlineRule` instances provide a regex pattern and `parse()` method. They return
`(node, end_index)`. If the rule does not accept a match, it returns
`(None, start_index)` so the parser can treat the marker as text.

## Root transforms

Rules can attach root transforms through their `root_transforms` attribute.
Transforms can:

- add required helper rules,
- collect document-wide definitions,
- defer inline parsing until definitions are known,
- update nodes after the whole tree is parsed.

Reference links, footnotes, abbreviations, and heading ID generation use this
mechanism.

## Parser state

`BlockState` stores the current line index, nesting depth, deferred inline
queues, and a per-parse `StateStore`. Built-in reference, footnote, and
abbreviation rules use that store through `StateKey` objects instead of fixed
fields on `BlockState`.

Because a new state and store are created for every top-level parse,
definitions do not leak between parser calls. Nested block parsing shares the
same store, so definitions found inside block quotes, lists, directives, or
footnotes remain visible to document-level transforms.

`StreamBlockState` wraps a line buffer for iterable sources. It supports
lookahead without forcing the entire input to be read immediately.

`state.source` is a source tracker. When positions are disabled it is a no-op;
when positions are enabled it maps line indexes and generated nested text back
to original source offsets. Use `state.source.line_position()`,
`state.source.line_text()`, or a collector from `state.source.collect()` when a
rule produces nodes or nested Markdown from a slice of the current source.

## Renderers

Renderers inherit from `BaseRenderer`, which dispatches by `node.type`.

```python
from wenmode.renderers import BaseRenderer


class PlainTextRenderer(BaseRenderer):
    pass
```

Register handlers with `BaseRenderer.register()` in renderer subclasses.

```python
from wenmode.nodes import Text
from wenmode.renderers import BaseRenderer, RenderContext


class UpperRenderer(BaseRenderer):
    pass


@UpperRenderer.register('text')
def render_text(renderer: UpperRenderer, node: Text, context: RenderContext) -> str:
    return node.value.upper()
```

If no handler is registered, `BaseRenderer` renders child nodes or a literal
`value` field. `HTMLRenderer` registers explicit handlers for Wenmode's node
types and falls back to the same child/value behavior for unknown nodes.
