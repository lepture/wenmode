---
description: Compare Wenmode with Mistune, Python-Markdown, markdown-it-py, markdown2, Marko, and commonmark.py for Python Markdown parsing, AST workflows, safety, streaming, and extensions.
---

(comparison)=
# Comparing Python Markdown parsers

```{rst-class} lead
Choose Wenmode when you need to control the Markdown pipeline, not only render
Markdown to HTML.
```

---

Python has several good Markdown libraries. Wenmode is not trying to replace
all of them for every use case. It is built for applications that need explicit
syntax rules, mdast-compatible AST output, safer HTML defaults, custom
renderers, or streaming.

If your application only needs a small Markdown-to-HTML helper and does not
inspect the parsed tree, another library may be enough. If Markdown is part of
your product model, Wenmode gives you more control over the pipeline.

## Quick comparison

| Need | Wenmode | Mistune | Python-Markdown | markdown-it-py | Marko |
| --- | --- | --- | --- | --- | --- |
| Markdown to HTML | yes | yes | yes | yes | yes |
| Explicit rule composition | yes | plugin-oriented | extension-oriented | rule-chain oriented | extension-oriented |
| mdast-compatible AST data | yes | custom AST renderer | no primary AST workflow | token stream | custom AST |
| Safer default HTML output | escapes raw HTML and sanitizes unsafe URLs | depends on configuration | depends on extensions and sanitization | depends on configuration | depends on renderer/configuration |
| Custom output formats | renderer handlers | custom renderer | extension/output hooks | renderer rules | renderer extensions |
| Product-specific dialects | rule lists and plugins | plugins | extensions | rules/plugins | extensions |
| Streaming HTML output | yes, with streaming-compatible rules | no primary streaming API | no primary streaming API | no primary streaming API | no primary streaming API |

This table is intentionally high level. Use the migration guides for concrete
code mappings and the benchmark page for measured local results.

## When Wenmode is a better fit

Choose Wenmode when your application needs one or more of these:

- A documented Markdown dialect for comments, docs, CMS fields, or AI output.
- AST-based validation, indexing, diagnostics, conversion, or storage.
- Safer default HTML rendering for user-authored content.
- Rules that can be enabled, removed, or packaged as product-specific plugins.
- Rendering the same parsed tree to HTML, Markdown, reStructuredText, AsciiDoc,
  or custom output.
- Streaming output for low-latency previews, uploads, or generated content.

The core distinction is that Wenmode treats parsing, rules, AST transforms, and
rendering as separate parts of the application pipeline.

## When another parser may be enough

Another Markdown library may be the simpler choice when:

- your application only calls `markdown_to_html(text)`;
- you already depend heavily on a mature extension ecosystem in that library;
- you do not need AST inspection, rule-level control, renderer policy, or
  streaming;
- preserving exact output compatibility with an existing integration matters
  more than changing the Markdown pipeline.

Wenmode has migration guides for applications that do need to move:

| Existing parser | Guide |
| --- | --- |
| Mistune | {doc}`migration/mistune` |
| Python-Markdown | {doc}`migration/python-markdown` |
| markdown-it-py | {doc}`migration/markdown-it-py` |
| markdown2 | {doc}`migration/markdown2` |
| Marko | {doc}`migration/marko` |
| commonmark.py | {doc}`migration/commonmark-py` |

## Performance snapshot

Wenmode includes a benchmark suite that compares the parser libraries covered
by the migration guides. See {ref}`benchmarks` for the current result table,
parser configuration, dependency versions, and edge-case benchmark notes.

For a deeper explanation of where Wenmode fits, read {doc}`Introduction
<introduce>`.
