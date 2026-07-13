---
description: Browse Wenmode reference pages for core block rules, core inline rules, extension rules, and AST node shapes.
---

(reference)=
# Reference

```{rst-class} lead
Look up Wenmode's public rules, generated node types, AST shapes, and default
HTML output.
```

---

This section is split by lookup task so syntax examples, AST shapes, and
renderer output stay readable as the rule set grows.

Use these pages after you know which feature you are looking for. If you are
still choosing a dialect, start with {ref}`presets` or {ref}`rule-matrix`.

Each rule entry shows the Markdown input and the AST shape produced by
`root.to_ast()`. The default HTML behavior follows from the built-in renderer
for that node type unless the entry says a directive renderer or plugin handler
is required.

```{toctree}
:maxdepth: 2

nodes
core-blocks
extension-blocks
core-inlines
extension-inlines
```

## Rule index

| Area | Rules |
| --- | --- |
| {doc}`Rule matrix <../rule-matrix>` | Preset membership, generated nodes, options, and streaming compatibility. |
| {doc}`Node model <nodes>` | Node groups, mdast-compatible fields, and AST conventions. |
| {doc}`Core block rules <core-blocks>` | CommonMark blocks, GFM tables and footnotes, task lists, and mdast block directives. |
| {doc}`Plugin block rules <extension-blocks>` | Block-level and document-wide syntax provided by built-in plugins. |
| {doc}`Core inline rules <core-inlines>` | CommonMark inlines, GFM strikethrough and autolinks, and mdast text directives. |
| {doc}`Plugin inline rules <extension-inlines>` | Inline syntax provided by built-in plugins. |

For generated Python API documentation, see {ref}`api`.
