---
description: Understand Wenmode node model, mdast-compatible AST shape, node groups, restoration behavior, and plugin node registration.
---

(reference-nodes)=
# Node model

```{rst-class} lead
Understand the common AST shape and node groups used by Wenmode rules.
```

---

AST examples in this reference use JSON-style output from `root.to_ast()`. The
top-level shape is always:

```json
{
  "type": "root",
  "children": []
}
```

Directive HTML can be replaced by registering directive renderers. Raw HTML is
escaped by the default `HTMLRenderer` unless you construct it with
`HTMLRenderer(escape=False)`.

Wenmode nodes are mdast-compatible data objects. Core Markdown, GFM, and shared
directive nodes live in `wenmode.nodes`. Plugin-specific nodes live in their
plugin modules and follow the same `Node.to_ast()` conventions.
Use `wenmode.nodes.BUILTIN_NODES` when you need the concrete core node class
list, for example when iterating over or comparing built-in node classes.

Renderers dispatch on the string stored in each node's `type` field. When a
custom renderer or plugin handler is not being called, check this value in the
AST first.

Use `wenmode.ast.walk()`, `wenmode.ast.find_all()`, and
`wenmode.ast.plain_text()` when you want to inspect node objects directly
instead of first converting the tree with `to_ast()`.

## Shape contract

Every serialized node has a non-empty string `type`. Nodes may also include
`data` and `position`. Fields whose value is `None` are omitted by `to_ast()`;
boolean `False`, empty lists, and empty strings are preserved.

Parent nodes use `children`, and literal nodes use `value`. Other fields are
node-specific:

| Type | Class | Fields beyond `type`, `data`, and `position` |
| --- | --- | --- |
| `root` | `Root` | `children` |
| `paragraph` | `Paragraph` | `children` |
| `heading` | `Heading` | `children`, `depth` |
| `blockquote` | `Blockquote` | `children` |
| `list` | `List` | `children`, `ordered`, `start`, `spread` |
| `listItem` | `ListItem` | `children`, `checked`, `spread` |
| `code` | `Code` | `value`, `lang`, `meta` |
| `thematicBreak` | `ThematicBreak` | none |
| `html` | `Html` | `value` |
| `text` | `Text` | `value` |
| `inlineCode` | `InlineCode` | `value` |
| `strong` | `Strong` | `children` |
| `emphasis` | `Emphasis` | `children` |
| `delete` | `Delete` | `children` |
| `table` | `Table` | `children`, `align` |
| `tableRow` | `TableRow` | `children` |
| `tableCell` | `TableCell` | `children` |
| `link` | `Link` | `children`, `url`, `title` |
| `image` | `Image` | `url`, `alt`, `title` |
| `break` | `Break` | none |
| `footnoteReference` | `FootnoteReference` | `identifier`, `label` |
| `footnoteDefinition` | `FootnoteDefinition` | `children`, `identifier`, `label` |
| `textDirective` | `TextDirective` | `children`, `name`, `attributes` |
| `leafDirective` | `LeafDirective` | `children`, `name`, `attributes` |
| `containerDirective` | `ContainerDirective` | `children`, `name`, `attributes` |
| `literalDirective` | `LiteralDirective` | `value`, `name`, `argument`, `attributes` |

Plugin nodes have the same common fields, but their concrete classes are only
restored by `from_ast()` when you pass plugin node classes:

| Type | Plugin class | Fields beyond `type`, `data`, and `position` |
| --- | --- | --- |
| `abbreviation` | `abbr.AbbreviationNode` | `children`, `title` |
| `definitionList` | `definition_list.DefinitionListNode` | `children` |
| `definitionTerm` | `definition_list.DefinitionTermNode` | `children` |
| `definitionDescription` | `definition_list.DefinitionDescriptionNode` | `children`, `spread` |
| `githubAlert` | `github_alert.GithubAlertNode` | `children`, `name` |
| `htmlContainer` | `html_container.HtmlContainerNode` | `children`, `name`, `attributes`, `opening`, `closing` |
| `math` | `block_math.MathNode` | `value` |
| `inlineMath` | `inline_math.InlineMathNode` | `value` |
| `blockSpoiler` | `block_spoiler.BlockSpoilerNode` | `children` |
| `inlineSpoiler` | `inline_spoiler.InlineSpoilerNode` | `children` |
| `mark` | `mark.MarkNode` | `children` |
| `insert` | `insert.InsertNode` | `children` |
| `superscript` | `superscript.SuperscriptNode` | `children` |
| `subscript` | `subscript.SubscriptNode` | `children` |
| `ruby` | `ruby.RubyNode` | `segments` |

`ruby.segments` is a list of `{"base": "...", "text": "..."}` mappings.
`htmlContainer.attributes` maps attribute names to strings or boolean `true`.
Escaped raw HTML and escaped HTML container boundaries use `data` with
`escaped` set to `true`.

Some plugins intentionally reuse core node types instead of defining custom
nodes. `frontmatter` stores metadata on `root.data["frontmatter"]`,
`inline_role` emits `textDirective`, and `fenced_directive` emits
`containerDirective` or `literalDirective`.

## AST interoperability

`wenmode.ast.from_ast()` converts a mdast-like mapping back into Wenmode node
objects. Built-in node types are restored from Wenmode's built-in node class
list:

```python
from wenmode.ast import from_ast

node = from_ast({
    'type': 'paragraph',
    'children': [{'type': 'text', 'value': 'Hello'}],
})
```

Plugin nodes live in their plugin modules. When you need concrete plugin node
classes after loading serialized AST data, collect node classes from the plugins
used by that Markdown dialect:

```python
from wenmode.ast import from_ast
from wenmode.plugins import block_math, html_container

node = from_ast({
    'type': 'math',
    'value': 'x + y\n',
}, nodes=[*html_container.nodes, *block_math.nodes])

assert type(node).__name__ == 'MathNode'
```

Each built-in plugin that defines custom node types exposes a `nodes` list.
Pass the node classes for the Markdown dialect whose AST data you want to
restore.

Unknown node types are preserved as generic `Parent`, `Literal`, or `Node`
instances by default so tools can round-trip data they do not understand. Pass
`unknown="error"` to reject unsupported node types instead.

Restoration is resource-bounded by default for serialized AST mappings. The
root node has depth `1`, every nested node mapping increases depth by `1`, and
every restored node mapping counts toward the node budget, including built-in
nodes, plugin nodes, and generic unknown nodes. The default budgets are
`max_depth=100` and `max_nodes=100_000`:

```python
node = from_ast(serialized_ast, max_depth=100, max_nodes=100_000)
```

Pass `max_depth=None` or `max_nodes=None` only for a trusted pipeline that has
accepted the corresponding risk. The `None` opt-out applies only to the
selected budget; reference-cycle detection and structural validation cannot be
disabled. If your application also needs a byte-size limit for untrusted JSON
or another serialized format, reject oversized payloads before decoding and
before calling `from_ast()`.

Restoration validates the common structural fields used by Wenmode nodes.
`children` must be a list of node mappings, literal `value` fields must be
strings, `data` must be a mapping when present, and heading `depth` must be an
integer from 1 through 6. Serialized field names beginning with `_` are
rejected because they represent private implementation state.

Parser-produced AST data can contain internal metadata that records an escaping
decision already made by Wenmode. The safe default rejects that metadata on
`html` nodes and on the reserved `htmlContainer` node type, including when the
plugin node class was not registered during restoration. Other unknown node
types retain extension data normally. For serialized data from a trusted
Wenmode pipeline, opt into its restoration explicitly:

```python
node = from_ast(trusted_wenmode_ast, allow_internal_metadata=True)
```

`allow_internal_metadata=True` is a trusted-input setting. It does not disable
structural validation and should not be used for AST mappings supplied by an
external client.

Raw CommonMark HTML remains the mdast-style literal `html` node with a `value`.
The `htmlContainer` node from `wenmode.plugins.html_container` is a Wenmode
extension node with `children`, similar in shape to MDX flow elements; it is not
the mdast core `html` node.

## Source positions

Nodes omit source positions by default. Construct `Wenmode(..., positions=True)`
or `Parser(..., positions=True)` when you need unist-style ranges in
`Root.to_ast()` output.

```json
{
  "type": "text",
  "position": {
    "start": {"line": 1, "column": 5, "offset": 4},
    "end": {"line": 1, "column": 9, "offset": 8}
  },
  "value": "text"
}
```

`line` and `column` are 1-based. `offset` is 0-based and counts Python string
characters from the beginning of the parsed source. For iterable line sources,
offsets are accumulated from the yielded lines.

Internally, `Position.start` and `Position.end` store only 0-based offsets.
`Root.to_ast()` converts those offsets to `line` and `column` values. Calling
`Node.to_ast()` on a standalone node, including nodes yielded by
`Parser.parse_iter()`, serializes positions with offsets only:

```json
{
  "type": "text",
  "position": {
    "start": {"offset": 4},
    "end": {"offset": 8}
  },
  "value": "text"
}
```

| Node group | Node types |
| --- | --- |
| Document and containers | `root`, `paragraph`, `heading`, `blockquote`, `list`, `listItem` |
| Literals | `text`, `inlineCode`, `code`, `html` |
| Formatting | `emphasis`, `strong`, `delete` |
| Links and media | `link`, `image`, `break` |
| GFM | `table`, `tableRow`, `tableCell`, `footnoteReference`, `footnoteDefinition` |
| Directives | `textDirective`, `leafDirective`, `containerDirective`, `literalDirective` |
| Plugin nodes | `abbreviation`, `definitionList`, `definitionTerm`, `definitionDescription`, `htmlContainer`, `math`, `inlineMath`, `mark`, `insert`, `superscript`, `subscript`, `ruby`, `inlineSpoiler`, `blockSpoiler` |

For the syntax that creates each node, continue with the block and inline rule
reference pages.
