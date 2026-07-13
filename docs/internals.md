---
description: Explore Wenmode internals including AST nodes, parser flow, rule dispatch, transforms, extension state, source maps, and renderer hooks.
---

(internals)=
# Internals

```{rst-class} lead
Explore Wenmode's node model, parser flow, rule dispatch, root transforms, state,
and renderer internals.
```

---

Wenmode is organized around a small set of data objects and dispatch points:
AST nodes, parser rules, root transforms, parser state, and renderers.

This page is for contributors and plugin authors who need to understand how
parsing and rendering are wired internally. For application usage, start with
{ref}`usage`, {ref}`presets`, and {ref}`custom-plugins`.

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
root transforms, and returns the root node. Rule-local node transforms run
during block parsing as soon as their owning rule returns a node.

At a high level:

1. Blank lines are skipped.
2. Block openers are matched against enabled `BlockRule` patterns.
3. If no block rule handles the line, the parser reads a paragraph.
4. Paragraph text is parsed with enabled inline rules.
5. Node transforms mutate nodes that can be finalized immediately.
6. Root transforms finalize document-wide features.

The important boundary for extension authors is that block parsing creates the
tree shape, inline parsing fills span-level children, node transforms handle
rule-local in-place updates, and root transforms handle features that need
document-wide state.

`Parser.parse_iter()` follows the block parser incrementally and yields nodes as
they are parsed. It rejects rule sets that attach parser transforms that cannot
stream.
Because it does not build a root node, position-aware `parse_iter()` output
keeps offset-only position data unless a caller supplies its own line mapping.
For iterable input, completed top-level source prefixes are released before the
corresponding node is yielded. Retained source is proportional to the current
unfinished block and any required parser lookahead; syntax that cannot emit a
block until it is complete may still retain that unfinished block. String input
is already resident and is not the bounded-memory streaming path.

`Parser` delegates most parsing work to private modules under `wenmode._parser`.
Those modules compile rule sets, dispatch block and inline rules, and decide
paragraph interruptions. They are intentionally private so the implementation
can change without creating a migration requirement for applications. Custom
rules should use `Parser.parse_blocks()`, `Parser.parse_inlines()`,
`Parser.inline_source()`, and `Parser.is_paragraph_interrupt()` rather than
importing `_parser` classes directly.

`Parser.parse_blocks()` is also the central container-depth boundary for nested
block parsing. It shares the enclosing parse store, deferred-inline queues,
callbacks, and inline source stack with the child state. While the parent state
is below `Parser.max_container_depth`, nested content runs through the normal
block parser. At the limit, the parser preserves the nested source as shallow
blank-separated paragraphs and still parses inline content with the supplied
source map. Extension rules should call this helper for nested block content
instead of instantiating their own recursive parser.

## Rules

All rules inherit from `Rule` and have a stable `name`. Enabled rules are
available as `parser.rules`, a read-only mapping keyed by rule name. The
`parser.block_rules`, `parser.inline_rules`, and `parser.root_transforms`
sequences are also read-only. Use `Parser.register_rule()` or
`Parser.register_rules()` to change the parser configuration; registration
rebuilds all compiled rule views.

`BlockRule` instances provide a block opener pattern and a `parse()` method.
They receive the parser, current block state, and the matched opener.

`ContinueRule` instances can inspect paragraph continuation lines. This is used
for syntax where a paragraph can become another block, such as setext headings.
Returning `None` declines the continuation and must leave `BlockState.index`
unchanged. Returning a replacement node must advance the state past the accepted
input.

`InlineRule` instances provide a regex pattern and `parse()` method. They return
`(node, end_index)`. If the rule does not accept a match, it returns
`(None, start_index)` so the parser can treat the marker as text.

## Node transforms

Rules can attach node transforms through their `node_transforms` attribute.
These transforms run immediately after a `BlockRule` or `ContinueRule` returns a
node, before that node is appended to its parent.

Use node transforms for behavior that can be decided from the current node plus
the per-parse `BlockState`, without waiting for the complete document. Heading
ID generation uses this path: the heading node is available immediately, while
the per-document slugger state lives in `BlockState.store`.

Node transforms mutate the supplied node in place and return `None`. They do not
replace the node returned by the owning rule. If a feature needs a different
node type or parent-level replacement, implement that behavior in the block or
continuation rule itself.

Node transforms that need finalized inline children can set
`defer_inlines=True`. During full parsing with deferred inline resolution, those
callbacks run after pending inline nodes are resolved. In streaming-compatible
configurations, inline parsing is not deferred, so the same transform still runs
before the node is yielded.

Because node transforms run during block parsing and do not need a complete
`Root`, they also run in `Parser.parse_iter()` and can support streaming output.

## Root transforms

Rules can attach root transforms through their `root_transforms` attribute.
Transforms can:

- add required helper rules,
- collect document-wide definitions,
- defer inline parsing until definitions are known,
- update nodes after the whole tree is parsed.

Reference links, footnotes, and abbreviations use this mechanism because
definitions found later in the document can affect earlier inline nodes.

Streaming never builds a complete `Root`, so every root transform blocks
`Parser.parse_iter()`. This is separate from `defer_inlines`: full parsing
defers inline parsing only for transforms that request it, while streaming
rejects root transforms because they require complete-root work.

## Parser state

`BlockState` stores the current line index, nesting depth, deferred inline
queues, and a per-parse `StateStore`. Built-in reference, footnote, and
abbreviation rules use that store through `StateKey` objects instead of fixed
fields on `BlockState`.

Block rules consume input with `state.advance()`. Fenced rules can use
`state.consume_until(is_closer, transform=None)` to collect body lines. It
consumes the closing line without returning it. `StreamBlockState` inherits the
same method, so rules do not need separate string and iterable-source paths.

Because a new state and store are created for every top-level parse,
definitions do not leak between parser calls. Nested block parsing shares the
same store, so definitions found inside block quotes, lists, directives, or
footnotes remain visible to document-level transforms.

`StreamBlockState` wraps a line buffer for iterable sources. It supports
lookahead without forcing the entire input to be read immediately. Its
`index`, `line_at()`, `has_index()`, `peek()`, and source positions use
absolute source indexes and offsets. `StreamBlockState.lines` is only the
currently buffered active window, not the full consumed source history. Custom
rules should use the state accessors instead of indexing `lines` directly when
they need absolute source positions or lookahead.

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

Register handlers on a renderer subclass when the behavior is application
specific. Register handlers through a plugin when the behavior belongs to a
syntax extension that other applications may reuse.

Renderer `root:pre` and `root:post` hooks run only when rendering a complete
root node. Incremental rendering does not synthesize an empty root or call hooks
with partial children. Class root hooks block streaming by default; the built-in
HTML and RST hooks are narrowly marked safe to omit because their supported
streaming fallbacks do not lose output. Instance hooks registered through
`register_handler()` always block streaming.
