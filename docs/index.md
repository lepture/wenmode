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

## Why Wenmode?

::::{grid} 1 1 2 2
:gutter: 2
:padding: 0
:class-row: surface

:::{grid-item-card} Explicit dialects
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

:::{grid-item-card} Safe HTML defaults
:link: security
:link-type: doc

Escape raw HTML and sanitize unsafe URLs by default, then opt into trusted
passthrough only when your application has a separate sanitization layer.
:::

:::{grid-item-card} Pluggable rendering
:link: recipes
:link-type: doc

Render HTML, normalized Markdown, reStructuredText, AsciiDoc, or
application-specific output with renderer handlers.
:::
::::

Parsing, rule selection, transforms, directive handling, and rendering are
separate pieces. Start with the default renderer, then opt into presets,
plugins, or AST workflows only when your application needs them.

## Start here

| Goal | Start here |
| --- | --- |
| Decide whether Wenmode fits your application | {doc}`Introduction <introduce>` |
| Parse Markdown and render HTML | {doc}`Usage <usage>` |
| Choose CommonMark, GFM, streaming, or custom rules | {doc}`Presets <presets>` |
| Add directives or non-standard syntax | {doc}`Directives <directives>` and {doc}`Plugins <plugins>` |
| Render user-authored Markdown safely | {doc}`Security <security>` |
| Build AST transforms, TOCs, or custom renderers | {doc}`Recipes <recipes>` |
| Integrate Wenmode into an application pipeline | {doc}`Integrations <integrations>` |
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
