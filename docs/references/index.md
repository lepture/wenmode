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
| {doc}`Node model <nodes>` | Node groups, mdast-compatible fields, and AST conventions. |
| {doc}`Core block rules <core-blocks>` | `AtxHeading`, `SetextHeading`, `ThematicBreak`, `FencedCode`, `IndentedCode`, `HtmlBlock`, `Blockquote`, `List`. |
| {doc}`Extension block rules <extension-blocks>` | `Table`, `Footnote`, `Abbreviation`, `DefinitionList`, `MathBlock`, `BlockSpoiler`, `LeafDirective`, `ContainerDirective`, `FencedDirective`. |
| {doc}`Core inline rules <core-inlines>` | `InlineCode`, `Emphasis`, `Link`, `Image`, `Autolink`, `RawHtml`, `BackslashEscape`, `CharacterReference`, `HardBreak`. |
| {doc}`Extension inline rules <extension-inlines>` | `Strikethrough`, `ExtendedAutolink`, `Mark`, `Insert`, `Superscript`, `Subscript`, `Ruby`, `InlineSpoiler`, `InlineMath`, `TextDirective`, `Role`. |

For generated Python API documentation, see {ref}`api`.
