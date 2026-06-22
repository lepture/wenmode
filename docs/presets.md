(presets)=
# Presets

```{rst-class} lead
Choose a ready-made rule set for CommonMark-style Markdown, GitHub-flavored
Markdown, or streaming output.
```

---

Presets are lists of rules. Pass one to `Wenmode` or `Parser` to select a
Markdown dialect.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
```

Use {ref}`plugins` for non-standard syntax that needs its own nodes and renderer
handlers.

In most applications, choose one preset first, then add plugins or custom rules
only for the syntax that preset does not cover.

## Choosing a preset

| Preset | Use it when | Includes | Main tradeoff |
| --- | --- | --- | --- |
| `commonmark` | You want the default Markdown behavior for articles, comments, or docs. | Core Markdown, reference links and images, inline HTML parsing. | No GFM tables, task list markers, footnotes, or bare URL autolinks. |
| `github` | You want GitHub-flavored Markdown output. | `commonmark`-style behavior plus the GFM feature set and disallowed HTML tag handling. | Requires full-document parsing, so it is not compatible with streaming output. |
| `streaming` | You need to emit HTML chunks as input arrives. | Most CommonMark-style rules, plus tables, strikethrough, direct links, and direct images. | Reference-style links, reference-style images, footnotes, and other deferred transforms are disabled. |
| Custom rule list | You are building a specific Markdown dialect or want to disable syntax. | Only the rules you pass. | You own the feature set and rule interactions. |

## CommonMark

`commonmark` is the default preset used by `Wenmode()`.

```python
from wenmode import Wenmode
from wenmode.presets import commonmark

wenmode = Wenmode(commonmark)
```

It enables the core Markdown features expected from a CommonMark-oriented
parser: thematic breaks, fenced and indented code, HTML blocks, lists, ATX and
setext headings, block quotes, hard breaks, autolinks, raw HTML, backslash
escapes, character references, images, links, inline code, and emphasis.

Reference-style links and images are enabled in this preset.

## GitHub

`github` extends the CommonMark-oriented behavior with GitHub-flavored Markdown
features.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
```

It adds tables, strikethrough, task list items, extended autolinks, and
footnotes. It configures `Table(require_body_pipe=False)` so GFM-compatible
table body rows can omit a pipe, and it configures HTML block and inline HTML
handling with the GFM disallowed HTML tag list.

## Streaming

`streaming` is built for incremental HTML output.

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)
text = '''
# Title

A [link](/url).
'''

html = ''.join(wenmode.stream(text))
```

It is close to the CommonMark-oriented rule set, with streaming-compatible GFM
tables and strikethrough enabled. It disables reference-style link and image
transforms by using `Image(references=False)` and `Link(references=False)`.
Direct links and images still work, while definitions and shortcut/reference
links stay as text.

This tradeoff lets Wenmode emit blocks before the end of the document. Rules
that need document-wide deferred inline transforms, such as reference links or
footnotes, are not compatible with streaming output.

## Custom preset

A preset is a reusable rule list. Create a custom one when your product needs a
smaller or stricter dialect than `commonmark`, `github`, or `streaming`.

Keep custom dialects in one module so the editor preview, API renderer,
background jobs, and tests all use the same Markdown behavior.

```python
from wenmode import Wenmode
from wenmode.presets import commonmark
from wenmode.rules import HtmlBlock, Image, Link, RawHtml

product_preset = [
    rule
    for rule in commonmark
    if rule not in {HtmlBlock, Image, Link, RawHtml}
]
product_preset.extend([
    Image(references=False),
    Link(references=False),
])

product_markdown = Wenmode(product_preset)
text = '''
<span>plain</span>

A [direct](/url) and [reference][id].
'''

html = product_markdown.render(text)

assert '&lt;span&gt;plain&lt;/span&gt;' in html
assert '<a href="/url">direct</a>' in html
assert '[reference][id]' in html
```

This example starts from `commonmark`, removes raw HTML parsing, and replaces
reference-style image and link rules with direct-only variants. Export
`product_preset` from your own package when multiple services need the same
syntax rules.

When a feature needs a new node type or renderer behavior, prefer a plugin over
a long shared rule list. See {ref}`plugins` and {ref}`custom-plugins`.
