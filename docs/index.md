# Wenmode

Wenmode is a composable Markdown toolkit for Python by the same author as
[Mistune](https://mistune.lepture.com/). It is a rewrite informed by Mistune's
design and years of Markdown parser usage, with a stronger focus on
composability, explicit rule sets, mdast-compatible AST output, extension
state, and pluggable rendering. It is intended to be a better foundation for
building Markdown dialects and renderers.

Wenmode separates parsing, rendering, syntax rules, and directive rendering so
you can start with a CommonMark-style parser and then opt in to only the
Markdown features you need.

The top-level `Wenmode` class combines a `Parser` and a renderer. By default it
parses CommonMark-style Markdown and renders HTML:

```python
from wenmode import Wenmode

wenmode = Wenmode()
html = wenmode.render('# Hello\n\nThis is **wenmode**.')
```

Use `parse()` when you need the syntax tree, `render()` when you need output,
and rule lists when you want a custom Markdown dialect.

The parsed tree is mdast-compatible: nodes use mdast-style `type` names such as
`root`, `paragraph`, `heading`, `link`, `image`, `emphasis`, and `strong`.
Wenmode also includes extension nodes for features such as tables, footnotes,
math, spoilers, ruby text, and directives.

```{toctree}
:maxdepth: 2
:caption: Guide

usage
presets
security
recipes
rules
reference
directives
internals
custom-rules
development
```
