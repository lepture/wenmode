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

Wenmode nodes are mdast-compatible data objects. Core Markdown nodes use
mdast-style names and fields, and extensions follow the same conventions with
explicit node types.

| Node group | Node types |
| --- | --- |
| Document and containers | `root`, `paragraph`, `heading`, `blockquote`, `list`, `listItem` |
| Literals | `text`, `inlineCode`, `code`, `html`, `math`, `inlineMath` |
| Formatting | `emphasis`, `strong`, `delete`, `mark`, `insert`, `superscript`, `subscript` |
| Links and media | `link`, `image`, `break` |
| GFM and extensions | `table`, `tableRow`, `tableCell`, `footnoteReference`, `footnoteDefinition`, `abbreviation`, `definitionList`, `definitionTerm`, `definitionDescription` |
| Wenmode extensions | `ruby`, `inlineSpoiler`, `blockSpoiler` |
| Directives | `textDirective`, `leafDirective`, `containerDirective` |
