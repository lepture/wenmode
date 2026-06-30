---
description: Decide whether Wenmode fits your Python Markdown integration before choosing presets, renderers, plugins, or migration guides.
---

(introduce)=
# Introduction

```{rst-class} lead
Use Wenmode when Markdown is part of your application model, not just a string
filter.
```

---

Wenmode is a Markdown toolkit for Python applications that need to control the
Markdown dialect they accept. It parses Markdown into node objects first, then
renders those nodes with an HTML, Markdown, reStructuredText, AsciiDoc, or custom
renderer.

That split is the core design choice. Parsing, rule selection, transforms,
directive handling, and rendering are separate pieces, so an application can
choose the behavior it needs instead of enabling one global extension bundle.

## What Wenmode optimizes for

Wenmode is built around five practical needs:

| Need | Wenmode feature |
| --- | --- |
| Keep Markdown behavior explicit | Choose `commonmark`, `github`, `streaming`, or an exact rule list. |
| Inspect or store parsed content | Parse to mdast-compatible node objects and `Node.to_ast()` dictionaries. |
| Render user-authored content safely | Escape raw HTML and sanitize unsafe URLs by default. |
| Add product-specific syntax | Package rules and renderer handlers with `Wenmode(..., plugins=[plugin])`. |
| Emit output incrementally | Use the `streaming` preset when deferred reference resolution is not needed. |

The common case still stays small:

```python
from wenmode import Wenmode

html = Wenmode().render('# Hello\n')

assert html == '<h1>Hello</h1>\n'
```

When you need the syntax tree, parse first:

```python
from wenmode import Wenmode
from wenmode.ast import find_all, plain_text
from wenmode.nodes import Heading

root = Wenmode().parse('# Hello\n\nA [link](/url).\n')
headings = find_all(root, Heading)

assert [plain_text(heading) for heading in headings] == ['Hello']
assert root.to_ast()['type'] == 'root'
```

## When Wenmode is a good fit

Use Wenmode when your application needs one or more of these behaviors:

- A documented Markdown dialect for comments, documentation, CMS content, or
  AI-generated Markdown.
- AST-based indexing, validation, transformation, diagnostics, or conversion.
- A safer default HTML path for user-authored content.
- Custom syntax that should be owned by your application instead of patched into
  a global renderer.
- Streaming previews or responses where direct links are enough and deferred
  references can stay disabled.

For example, a documentation system might parse once, add heading IDs, collect a
table of contents, store AST JSON for search, and render HTML from the same
tree. A product comment renderer might use the `github` preset but keep raw HTML
escaped. A migration from another parser might start with `Wenmode().render()`
and later move extension behavior into explicit plugins.

## When to choose something else

Wenmode is not trying to be a drop-in wrapper around every Python Markdown
library. A smaller helper may be enough when your application only calls
`markdown_to_html(text)` and never inspects the AST, changes syntax, streams
output, or controls extension boundaries.

Also avoid treating `HTMLRenderer(escape=False)` as a sanitizer. It is a raw
HTML passthrough setting for trusted or separately sanitized content. Start with
the default renderer for untrusted Markdown and review {ref}`security` before
changing safety settings.

## How to read the docs

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
