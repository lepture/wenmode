(integrations)=
# Integrations

```{rst-class} lead
Build reusable Markdown pipelines with safe defaults, AST export, and streaming.
```

---

Use this page when you are wiring Wenmode into an application rather than
trying one API call. The examples keep parser setup, rendering policy, and
post-processing in one place so the behavior is easy to test.

The main integration rule is: configure Markdown once, then reuse that
configuration everywhere the same content type is rendered. Avoid letting the
editor preview, API response, and background indexing job drift into different
rule sets.

## Repository examples

The repository includes local example packages that show Wenmode embedded in web
and documentation frameworks:

- `examples/wenmode-fastapi` is a FastAPI app that streams uploaded Markdown
  files through `StreamingResponse`.
- `examples/wenmode-mkdocs` is a MkDocs plugin that renders page Markdown
  through Wenmode before MkDocs finishes the page build.
- `examples/wenmode-myst` is a Sphinx source parser that uses Wenmode instead
  of `myst_parser` for Markdown input.

The Wenmode documentation itself uses the `wenmode_myst` example. The Sphinx
configuration adds `examples/wenmode-myst/src` to `sys.path` and enables the
`wenmode_myst` extension, so these docs are built by parsing Markdown with
Wenmode, rendering it to reStructuredText, and handing that generated text back
to Sphinx.

## Reuse one configured instance

Create a small service object around the rule set your product supports. A
`Wenmode` instance can be reused across calls; render state is created per
render operation.

```python
from wenmode import Wenmode
from wenmode.presets import github


class MarkdownService:
    def __init__(self, wenmode: Wenmode | None = None) -> None:
        self.wenmode = wenmode if wenmode is not None else Wenmode(github)

    def render_comment(self, text: str) -> str:
        return self.wenmode.render(text)


service = MarkdownService()
text = '''
- [x] ship docs

Visit https://example.com
'''

html = service.render_comment(text)

assert '<input checked="" disabled="" type="checkbox">' in html
assert '<a href="https://example.com">https://example.com</a>' in html
```

## Render untrusted user content

For comments, profile fields, forum posts, and other user-authored Markdown,
start with the default HTML renderer. It escapes raw HTML and removes unsafe
link targets.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
text = '''
Hello <script>alert(1)</script>.

[bad](javascript:alert(1))
'''

html = wenmode.render(text)

assert '&lt;script>alert(1)&lt;/script>' in html
assert '<a>bad</a>' in html
assert 'javascript:alert' not in html
```

If your application also wants raw HTML syntax to stay as plain text in the AST,
remove the raw HTML parser rules as shown in {ref}`recipes`.

## Publish documentation pages

Documentation sites often need the rendered body, a table of contents, and a
machine-readable AST for search or indexing. Parse once, then run tree
transforms before rendering.

```python
import json

from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids
from wenmode.toc import collect_toc, render_toc_html


class RenderedPage:
    def __init__(self, html: str, toc_html: str, ast_json: str) -> None:
        self.html = html
        self.toc_html = toc_html
        self.ast_json = ast_json


def render_page(source: str) -> RenderedPage:
    root = Wenmode().parse(source)
    add_heading_ids(root, slugger=Slugger(), min_depth=2)

    toc = collect_toc(root, min_depth=2, max_depth=3)
    toc_html = render_toc_html(toc)
    body_html = HTMLRenderer().render(root)

    return RenderedPage(
        html=toc_html + body_html,
        toc_html=toc_html,
        ast_json=json.dumps(root.to_ast(), ensure_ascii=False),
    )


text = '''
# Guide

## Install

Run **wenmode**.
'''

page = render_page(text)

assert '<a href="#install">Install</a>' in page.toc_html
assert '<h2 id="install">Install</h2>' in page.html
assert '"type": "root"' in page.ast_json
```

## Stream low-latency previews

Use the `streaming` preset for live previews, chat responses, or other views
that should emit HTML chunks before the whole document is available. Keep
reference-style links, footnotes, and other deferred features out of this path.

```python
from collections.abc import Iterable

from wenmode import Wenmode
from wenmode.presets import streaming

preview = Wenmode(streaming)


def render_preview(lines: Iterable[str]) -> Iterable[str]:
    yield '<article class="preview">\n'
    yield from preview.stream(lines)
    yield '</article>\n'


chunks = list(
    render_preview(
        [
            '# Preview\n',
            '\n',
            'A [link](https://example.com).\n',
        ]
    )
)
html = ''.join(chunks)

assert html.startswith('<article class="preview">')
assert '<h1>Preview</h1>' in html
assert '<a href="https://example.com">link</a>' in html
```

See {ref}`rule-matrix` for rules that are not compatible with streaming.

## Package a product dialect

When multiple services need the same Markdown behavior, keep the rule list and
plugin list in one application module and expose a small factory. Import that
factory everywhere instead of rebuilding slightly different `Wenmode` instances
in each service. This avoids subtle differences between the editor preview, API
rendering, background jobs, and test fixtures.

```python
from wenmode import Wenmode
from wenmode.plugins import frontmatter, math
from wenmode.presets import commonmark
from wenmode.rules import HtmlBlock, RawHtml

product_rules = [rule for rule in commonmark if rule not in {HtmlBlock, RawHtml}]
product_plugins = [frontmatter, math]


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
plugin that registers parser rules and renderer handlers together. See
{ref}`custom-plugins` for an RST-inspired example that creates a new node type
and registers HTML, Markdown, and RST rendering behavior.
