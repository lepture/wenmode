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

Renderers dispatch on the string stored in each node's `type` field. When a
custom renderer or plugin handler is not being called, check this value in the
AST first.

Use `wenmode.ast.walk()`, `wenmode.ast.find_all()`, and
`wenmode.ast.plain_text()` when you want to inspect node objects directly
instead of first converting the tree with `to_ast()`.

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
| Plugin nodes | `abbreviation`, `definitionList`, `definitionTerm`, `definitionDescription`, `math`, `inlineMath`, `mark`, `insert`, `superscript`, `subscript`, `ruby`, `inlineSpoiler`, `blockSpoiler` |

For the syntax that creates each node, continue with the block and inline rule
reference pages.
