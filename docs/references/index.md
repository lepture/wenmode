(reference)=
# Reference

```{rst-class} lead
Look up Wenmode's public rules, generated node types, AST shapes, and default
HTML output.
```

---

This section is split by lookup task so syntax examples, AST shapes, and
renderer output stay readable as the rule set grows.

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
| {doc}`Core block rules <core-blocks>` | `AtxHeading`, `SetextHeading`, `ThematicBreak`, `FencedCode`, `IndentedCode`, `HtmlBlock`, `Blockquote`, `List`. |
| {doc}`Extension block rules <extension-blocks>` | GFM tables and footnotes, mdast block directives, and block-level plugin syntax. |
| {doc}`Core inline rules <core-inlines>` | `InlineCode`, `Emphasis`, `Link`, `Image`, `Autolink`, `RawHtml`, `BackslashEscape`, `CharacterReference`, `HardBreak`. |
| {doc}`Extension inline rules <extension-inlines>` | GFM inline syntax, mdast text directives, and inline plugin syntax. |

For generated Python API documentation, see {ref}`api`.
