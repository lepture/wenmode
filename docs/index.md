---
layout: landing
description: Wenmode is a fast, composable Markdown toolkit for Python with explicit rule composition, mdast-compatible AST output, safe HTML defaults, streaming, and pluggable rendering.
---

(index)=
# Wenmode

```{rst-class} lead
Build a Markdown dialect with explicit rules, AST output, safe defaults, and
pluggable renderers.
```

```{container} buttons
{doc}`Introduction <introduce>`
{doc}`Quick Start <usage>`
```

Wenmode is for Python applications where Markdown is part of the product model:
documentation systems, user-generated content, static-site pipelines, AI/AST
workflows, custom dialects, and format converters.

## Quick start

Install Wenmode from PyPI:

```bash
pip install wenmode
```

Render Markdown with the default CommonMark-style rules and safer HTML defaults:

```python
from wenmode import Wenmode

html = Wenmode().render('# Hello\n')

assert html == '<h1>Hello</h1>\n'
```

## Why Wenmode?

::::{grid} 1 1 2 2
:gutter: 2
:padding: 0
:class-row: surface

:::{grid-item-card} From Mistune's author
:link: introduce
:link-type: doc

Wenmode comes from the same author as
[Mistune](https://mistune.lepture.com/), redesigned for applications that need
to own the full Markdown pipeline.
:::

:::{grid-item-card} Explicit rule composition
:link: presets
:link-type: doc

Choose CommonMark-style Markdown, GitHub-flavored Markdown, streaming output, or
the exact rule list your product needs.
:::

:::{grid-item-card} AST-first workflows
:link: references/nodes
:link-type: doc

Parse to mdast-compatible nodes before indexing, transforming, storing,
validating, or rendering content.
:::

:::{grid-item-card} Safer HTML defaults
:link: security
:link-type: doc

Escape raw HTML and sanitize unsafe URLs by default, then opt into trusted
passthrough only when your application has a separate sanitization layer.
:::
::::

Parsing, rule selection, transforms, directive handling, and rendering are
separate pieces. Start with the default renderer, then opt into presets,
plugins, or AST workflows only when your application needs them.

## Markdown pipeline

Wenmode keeps the Markdown pipeline explicit:

```text
Markdown source
  -> Parser + explicit rules
  -> mdast-compatible nodes
  -> transforms, validation, storage, or indexing
  -> HTML, Markdown, reStructuredText, AsciiDoc, or custom output
```

That split lets one application parse once, generate heading IDs, collect a
table of contents, store AST JSON for search, and render HTML from the same
tree.

## Project status

::::{grid} 1 1 2 2
:gutter: 2
:padding: 0

:::{grid-item-card} Tested Markdown coverage
:link: compliance
:link-type: doc

Wenmode runs CommonMark and GitHub-flavored Markdown fixture suites in its test
suite, with documented compatibility boundaries.
:::

:::{grid-item-card} Modern Python support
:link: compatibility
:link-type: doc

The package supports Python 3.10 and newer, including current CPython releases
and PyPy versions covered by the project metadata.
:::
::::

## Start here

| Goal | Start here |
| --- | --- |
| Decide whether Wenmode fits your application | {doc}`Introduction <introduce>` |
| Parse Markdown and render HTML | {doc}`Usage <usage>` |
| Choose CommonMark, GFM, streaming, or custom rules | {doc}`Presets <presets>` |
| Add directives or non-standard syntax | {doc}`Directives <directives>` and {doc}`Plugins <plugins>` |
| Render user-authored Markdown safely | {doc}`Security <security>` |
| Parse and filter AI-generated Markdown | {doc}`AI Markdown <recipes/ai-generated-markdown>` |
| Build AST transforms, TOCs, or custom renderers | {doc}`Recipes <recipes/index>` |
| Integrate Wenmode into an application pipeline | {doc}`Integrations <integrations>` |
| Compare Python Markdown parsers | {doc}`Comparison <comparison>` |
| Migrate from another Markdown parser | {doc}`Migration guides <migration/index>` |
| Check compatibility and project status | {doc}`Compatibility <compatibility>` |

```{toctree}
:caption: User Guide
:hidden:
:maxdepth: 2

introduce
usage
presets
directives
plugins
security
recipes/index
integrations
comparison
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
