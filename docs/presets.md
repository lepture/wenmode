# Presets

Presets are lists of rules. Pass one to `Wenmode` or `Parser` to select a
Markdown dialect.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
```

## Choosing a preset

| Preset | Use it when | Includes | Main tradeoff |
| --- | --- | --- | --- |
| `commonmark` | You want the default Markdown behavior for articles, comments, or docs. | Core Markdown, reference links and images, inline HTML parsing. | No GFM tables, task list markers, footnotes, or bare URL autolinks. |
| `github` | You want GitHub-flavored Markdown output. | `commonmark`-style behavior plus tables, task list items, strikethrough, extended autolinks, footnotes, and GFM disallowed HTML tag handling. | Requires full-document parsing, so it is not compatible with streaming output. |
| `streaming` | You need to emit HTML chunks as input arrives. | Most CommonMark-style rules, with direct links and images. | Reference-style links, reference-style images, footnotes, and other deferred transforms are disabled. |
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
footnotes. It also configures HTML block and inline HTML handling with the GFM
disallowed HTML tag list.

## Streaming

`streaming` is built for incremental HTML output.

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)
html = ''.join(wenmode.stream('# Title\n\nA [link](/url).\n'))
```

It is close to the CommonMark-oriented rule set, but disables reference-style
link and image transforms by using `Image(references=False)` and
`Link(references=False)`. Direct links and images still work, while definitions
and shortcut/reference links stay as text.

This tradeoff lets Wenmode emit blocks before the end of the document. Rules
that need document-wide deferred inline transforms, such as reference links or
footnotes, are not compatible with streaming output.
