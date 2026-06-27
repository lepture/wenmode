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

wen = Wenmode(github)
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
| `streaming` | You need to emit HTML chunks as input arrives. | Most CommonMark-style rules, plus tables, strikethrough, direct links, and direct images. | Reference-style links, reference-style images, footnotes, and other deferred document-wide transforms are disabled. |
| Custom rule list | You are building a specific Markdown dialect or want to disable syntax. | Only the rules you pass. | You own the feature set and rule interactions. |

## CommonMark

`commonmark` is the default preset used by `Wenmode()`.

```python
from wenmode import Wenmode
from wenmode.presets import commonmark

wen = Wenmode(commonmark)
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

wen = Wenmode(github)
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

wen = Wenmode(streaming)
text = '''
# Title

A [link](/url).
'''

html = ''.join(wen.stream(text))
```

It is close to the CommonMark-oriented rule set, with streaming-compatible GFM
tables and strikethrough enabled. Direct links and images still work:
`[label](/url)` and `![alt](/image.png)` are parsed normally.

The preset disables reference-style link and image transforms by using
`Image(references=False)` and `Link(references=False)`. Definitions,
shortcut/reference links, and shortcut/reference images stay as text.
Footnotes are not enabled. Other features that need deferred document-wide
transforms, such as abbreviation rewriting, are not compatible with streaming
output.

This tradeoff lets Wenmode emit blocks before the end of the document. If a
custom streaming configuration enables a deferred rule or plugin, `stream()`
raises `StreamingUnsupportedError` instead of emitting partial output with
missing document-wide context.

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

wen = Wenmode(product_preset)
text = '''
<span>plain</span>

A [direct](/url) and [reference][id].
'''

html = wen.render(text)

assert '&lt;span&gt;plain&lt;/span&gt;' in html
assert '<a href="/url">direct</a>' in html
assert '[reference][id]' in html
```

This example starts from `commonmark`, removes raw HTML parsing, and replaces
reference-style image and link rules with direct-only variants. Export
`product_preset` from your own package when multiple services need the same
syntax rules.

Use `create_preset()` when you want that derivation to match rules by their
stable names:

```python
from wenmode import Wenmode
from wenmode.presets import commonmark, create_preset
from wenmode.rules import HtmlBlock, Image, Link, RawHtml, Strikethrough

product_preset = create_preset(
    commonmark,
    remove=[HtmlBlock, RawHtml],
    replace=[Image(references=False), Link(references=False)],
    append=[Strikethrough],
)

wen = Wenmode(product_preset)

assert wen.render('<span>plain</span>\n') == (
    '<p>&lt;span&gt;plain&lt;/span&gt;</p>\n'
)
assert wen.render('[x]: /url\n\n[x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n'
assert '<del>old</del>' in wen.render('~~old~~\n')
```

`replace` keeps each configured rule in the same position as the rule it
replaces. Use `prepend` or `append` for rules that are not already present in
the base preset.

When a feature needs a new node type or renderer behavior, prefer a plugin over
a long shared rule list. See {ref}`plugins` and {ref}`custom-plugins`.
