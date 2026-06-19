---
layout: landing
description: Wenmode is a fast, composable Markdown toolkit for Python with explicit rule composition, mdast-compatible AST output, safe HTML defaults, streaming, and pluggable rendering.
---

(index)=
# Wenmode

```{rst-class} lead
Build exactly the Markdown dialect your Python application needs. Wenmode gives
you fast CommonMark-style parsing, explicit rule composition, mdast-compatible
AST output, safe HTML defaults, streaming, and pluggable renderers.
```

```{container} buttons
{doc}`Quick Start <usage>`
{doc}`Recipes <recipes>`
```

Wenmode is designed for applications that need more control than a single
Markdown-to-HTML helper can provide: documentation systems, user-generated
content, static-site pipelines, AI/AST workflows, custom Markdown dialects, and
format converters.

## Why Wenmode?

::::{grid} 1 1 2 3
:gutter: 2
:padding: 0
:class-row: surface

:::{grid-item-card} Composable syntax
:link: presets
:link-type: doc

Start with CommonMark-style Markdown, switch to GitHub-flavored Markdown, use
streaming output, or pass the exact rule list your product needs.
:::

:::{grid-item-card} AST-first workflows
:link: references/nodes
:link-type: doc

Parse to mdast-compatible nodes for indexing, transforms, storage, analysis,
or conversion before choosing an output format.
:::

:::{grid-item-card} Pluggable output
:link: recipes
:link-type: doc

Render HTML, normalized Markdown, reStructuredText, or your own output by
registering handlers for the node types you care about.
:::

:::{grid-item-card} Safe HTML defaults
:link: security
:link-type: doc

Escape raw HTML and sanitize unsafe URLs by default, then opt into trusted HTML
only when your application has a separate sanitization layer.
:::

:::{grid-item-card} Streaming support
:link: usage
:link-type: doc

Emit HTML chunks as Markdown is parsed when latency matters, using a preset that
avoids document-wide deferred resolution.
:::

:::{grid-item-card} Fast and lightweight
:link: compatibility
:link-type: doc

Keep runtime dependencies at zero and enable only the syntax rules you need, so
larger dialects do not become the default cost for every parse.
:::
::::

Wenmode separates parsing, rendering, syntax rules, and directive rendering so
you can start with a CommonMark-style parser and then opt in to only the
Markdown features you need.

Install Wenmode from PyPI:

::::{tab-set}
:class: outline

:::{tab-item} {iconify}`devicon:pypi` pip

```bash
pip install wenmode
```
:::

:::{tab-item} {iconify}`material-icon-theme:uv` uv

```bash
uv add wenmode
```
:::
::::

```python
from wenmode import Wenmode

wenmode = Wenmode()
text = '''
# Hello

This is **wenmode**.
'''
expected = '''
<h1>Hello</h1>
<p>This is <strong>wenmode</strong>.</p>
'''

html = wenmode.render(text)

assert html == expected.lstrip()
```

## Choose your path

| Goal | Start here |
| --- | --- |
| Parse Markdown and render HTML | {doc}`Usage <usage>` |
| Choose CommonMark, GFM, streaming, or a custom dialect | {doc}`Presets <presets>` |
| Use mdast-style directives | {doc}`Directives <directives>` |
| Enable non-standard syntax | {doc}`Plugins <plugins>` |
| Render user-authored Markdown safely | {doc}`Security <security>` |
| Add a table of contents, heading IDs, or a custom renderer | {doc}`Recipes <recipes>` |
| Build application pipelines around Wenmode | {doc}`Integrations <integrations>` |
| Troubleshoot escaping, directives, streaming, or custom renderers | {doc}`Troubleshooting <troubleshooting>` |
| Migrate from another Markdown parser | {doc}`Migration guides <migration/index>` |
| Review benchmark methodology and results | {doc}`Benchmarks <benchmarks>` |
| Create custom plugins | {doc}`Custom plugins <custom-plugins>` |
| Check compatibility, compliance, changelog, and project status | {doc}`Compatibility <compatibility>`, {doc}`Compliance <compliance>`, and {doc}`Changelog <changelog>` |

```{toctree}
:caption: User Guide
:hidden:
:maxdepth: 2

usage
presets
directives
plugins
security
recipes
integrations
migration/index
troubleshooting
```

```{toctree}
:caption: Reference
:hidden:
:maxdepth: 2

references/index
rule-matrix
api
```

```{toctree}
:caption: Developer Guide
:hidden:
:maxdepth: 2

rules
custom-plugins
internals
development
```

```{toctree}
:caption: Project
:hidden:
:maxdepth: 2

compatibility
compliance
benchmarks
changelog
```
