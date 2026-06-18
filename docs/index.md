---
layout: landing
description: Wenmode is a composable Markdown toolkit for Python with explicit rule composition, mdast-compatible AST output, and pluggable rendering.
---

(index)=
# Wenmode

```{rst-class} lead
Wenmode is a composable Markdown toolkit for building Python Markdown dialects,
AST workflows, and renderers.
```

```{container} buttons
{doc}`User Guide <usage>`
{doc}`Recipes <recipes>`
```

::::{grid} 1 1 2 3
:gutter: 2
:padding: 0
:class-row: surface

:::{grid-item-card} User Guide
:link: usage
:link-type: doc

Start with parsing Markdown, rendering HTML, choosing presets, and applying
security defaults.
:::

:::{grid-item-card} Developer Guide
:link: custom-rules
:link-type: doc

Build custom syntax rules, understand parser internals, and work with extension
state and transforms.
:::

:::{grid-item-card} Contributor Guide
:link: development
:link-type: doc

Run the local test, lint, type-check, benchmark, and documentation workflows.
:::
::::

Wenmode separates parsing, rendering, syntax rules, and directive rendering so
you can start with a CommonMark-style parser and then opt in to only the
Markdown features you need.

```python
from wenmode import Wenmode

wenmode = Wenmode()
html = wenmode.render('# Hello\n\nThis is **wenmode**.')

assert html == '<h1>Hello</h1>\n<p>This is <strong>wenmode</strong>.</p>\n'
```

```{toctree}
:caption: User Guide
:hidden:
:maxdepth: 2

usage
presets
security
recipes
directives
```

```{toctree}
:caption: Developer Guide
:hidden:
:maxdepth: 2

rules
custom-rules
internals
reference
```

```{toctree}
:caption: Contributor Guide
:hidden:
:maxdepth: 2

development
```
