---
description: Understand where Wenmode fits before choosing presets, renderers, plugins, or migration guides.
---

(introduce)=
# Introduction

```{rst-class} lead
Use Wenmode when Markdown is part of your application model, not just a string
filter.
```

---

Wenmode is a Markdown toolkit for Python applications that need explicit control
over parsing and rendering. It parses Markdown into mdast-compatible node
objects, then renders those nodes as HTML, Markdown, reStructuredText, AsciiDoc,
or application-specific output.

The default API is still small:

```python
from wenmode import Wenmode

html = Wenmode().render('# Hello\n')

assert html == '<h1>Hello</h1>\n'
```

The rest of the library exists for applications that need to inspect the tree,
choose a dialect, add syntax, or enforce rendering policy.

## Core model

Wenmode keeps the Markdown pipeline split into explicit pieces:

| Piece | Responsibility |
| --- | --- |
| Presets and rules | Define the Markdown dialect. |
| Parser | Turns source text into node objects. |
| AST helpers and transforms | Inspect, validate, or modify parsed content. |
| Renderers | Convert nodes to HTML, Markdown, RST, AsciiDoc, or custom output. |
| Plugins | Package custom rules, nodes, renderer handlers, and options. |

This split lets one application parse once, add heading IDs, collect a table of
contents, store AST JSON for search, and render HTML from the same tree. Another
application can keep the same parser but swap the renderer or safety policy.

## When Wenmode is a good fit

Use Wenmode when your application needs one or more of these:

- A documented Markdown dialect for comments, documentation, CMS content, or
  AI-generated Markdown.
- AST-based indexing, validation, transformation, diagnostics, or conversion.
- A safer default HTML path for user-authored content.
- Product-specific syntax packaged as plugins.
- Streaming output where deferred document-wide features can stay disabled.

## When to choose something else

Wenmode is not trying to be a drop-in wrapper around every Python Markdown
library. A smaller helper may be enough when your application only calls
`markdown_to_html(text)` and never inspects the AST, changes syntax, streams
output, or controls extension boundaries.

Also do not treat `HTMLRenderer(escape=False)` as a sanitizer. It is a raw HTML
passthrough setting for trusted or separately sanitized content. Start with the
default renderer for untrusted Markdown and review {ref}`security` before
changing safety settings.

## Where to go next

If you are evaluating Wenmode, start here and then choose the path that matches
your task:

| Goal | Next page |
| --- | --- |
| Render Markdown in a new project | {doc}`Usage <usage>` |
| Pick CommonMark, GFM, streaming, or custom rules | {doc}`Presets <presets>` |
| Add extra syntax such as math or definition lists | {doc}`Plugins <plugins>` |
| Handle untrusted user content | {doc}`Security <security>` |
| Build AST transforms or app pipelines | {doc}`Recipes <recipes>` and {doc}`Integrations <integrations>` |
| Move from another Python Markdown parser | {doc}`Migration guides <migration/index>` |
| Check compatibility and project status | {doc}`Compatibility <compatibility>` and {doc}`Compliance <compliance>` |
