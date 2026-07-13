---
description: Build reusable Wenmode integration pipelines by configuring Markdown once, sharing application factories, and reusing examples across services.
---

(integrations)=
# Integrations

```{rst-class} lead
Build reusable Markdown pipelines with safe defaults, AST export, and streaming.
```

---

Use this page when you are wiring Wenmode into an application rather than
trying one API call. Keep parser setup, rendering policy, plugins, and
post-processing in one place so the behavior is easy to test.

The main integration rule is: configure Markdown once, then reuse that
configuration everywhere the same content type is rendered. Avoid letting the
editor preview, API response, and background indexing job drift into different
rule sets.

## Reuse one configured instance

Create a small service object around the rule set your product supports. A
`Wenmode` instance can be reused across calls; render state is created per
render operation.

```python
from wenmode import Wenmode
from wenmode.presets import github


class MarkdownService:
    def __init__(self, wen: Wenmode | None = None) -> None:
        self.wen = wen if wen is not None else Wenmode(github)

    def render_comment(self, text: str) -> str:
        return self.wen.render(text)


service = MarkdownService()
text = '''
- [x] ship docs

Visit https://example.com
'''

html = service.render_comment(text)

assert '<input checked="" disabled="" type="checkbox">' in html
assert '<a href="https://example.com">https://example.com</a>' in html
```

## Choose focused patterns

Use focused guides for details that are not specific to application wiring:

| Goal | Start here |
| --- | --- |
| Render untrusted user-authored Markdown | {ref}`security` |
| Add heading IDs or a table of contents | {doc}`recipes/table-of-contents` |
| Store or inspect AST JSON | {doc}`recipes/ast-workflows` |
| Stream generated Markdown or filter nodes | {doc}`recipes/ai-generated-markdown` |
| Stream ordinary Markdown chunks | {ref}`usage` and the `streaming` preset in {ref}`presets` |
| Compare rule streaming compatibility | {ref}`rule-matrix` |

## Package a product dialect

When multiple services need the same Markdown behavior, keep the rule list and
plugin list in one application module and expose a small factory. Import that
factory everywhere instead of rebuilding slightly different `Wenmode` instances
in each service. This avoids subtle differences between the editor preview, API
rendering, background jobs, and test fixtures.

```python
from wenmode import Wenmode
from wenmode.plugins import block_math, frontmatter, inline_math
from wenmode.presets import commonmark, create_preset
from wenmode.rules import HtmlBlock, RawHtml

product_rules = create_preset(commonmark, remove=[HtmlBlock, RawHtml])
product_plugins = [frontmatter, inline_math, block_math]


def create_product_markdown(**options):
    return Wenmode(product_rules, plugins=product_plugins, **options)

text = '''---
title: Preview
---

<span>plain text in our dialect</span>

Inline $x + y$.
'''
expected = '''
<p>&lt;span&gt;plain text in our dialect&lt;/span&gt;</p>
<p>Inline <span class="math math-inline">x + y</span>.</p>
'''

html = create_product_markdown().render(text)

assert html == expected.lstrip()
```

Pass renderer or parsing options through the same factory when another layer
needs a different output format or source positions. For new syntax, create a
plugin that registers parser rules and renderer handlers together; see
{ref}`custom-plugins`.

## Repository examples

The repository includes local example packages that show Wenmode embedded in web
and documentation frameworks:

- `examples/wenmode-fastapi` is a FastAPI app that streams uploaded Markdown
  files through `StreamingResponse`.
- `examples/wenmode-mkdocs` is a MkDocs plugin that renders page Markdown
  through Wenmode before MkDocs finishes the page build.
- `examples/wenmode-myst` is a Sphinx source parser that uses Wenmode instead
  of `myst_parser` for Markdown input.

These docs use the `wenmode_myst` example: Sphinx loads the extension from
`examples/wenmode-myst/src`, then Wenmode converts Markdown to reStructuredText
before Sphinx parses it.
