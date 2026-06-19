(troubleshooting)=
# Troubleshooting

```{rst-class} lead
Diagnose common Wenmode integration issues around raw HTML, URL sanitization,
directives, streaming, custom renderers, and rule selection.
```

---

## Raw HTML is escaped

`HTMLRenderer()` escapes raw HTML nodes by default. This is the recommended
setting for user-authored Markdown.

Use raw HTML passthrough only for trusted or separately sanitized content:

```python
from wenmode import HTMLRenderer, Wenmode

wenmode = Wenmode(renderer=HTMLRenderer(escape=False))
```

If you do not want raw HTML syntax to become `html` nodes at all, remove
`HtmlBlock` and `RawHtml` from the rule list. See {ref}`security`.

## Links render without href

`HTMLRenderer()` drops unsafe URL schemes by default. For example,
`javascript:` links render without `href`.

```python
from wenmode import Wenmode

html = Wenmode().render('[x](javascript:alert(1))')
assert html == '<p><a>x</a></p>\n'
```

Use `HTMLRenderer(sanitize_urls=False)` only when URL validation is handled
outside Wenmode.

## A directive parses but does not render custom HTML

Directive syntax rules and directive renderers are separate. Enabling
`ContainerDirective`, `LeafDirective`, `TextDirective`, or the
`wenmode.plugins.fenced_directive` and `wenmode.plugins.inline_role` plugins
only creates directive nodes. Register a directive renderer when you want
special HTML output.

```python
from wenmode import Wenmode
from wenmode.directives import Admonition
from wenmode.rules import ContainerDirective

wenmode = Wenmode([ContainerDirective], directives=[Admonition()])
```

Without a matching directive renderer, Wenmode falls back to rendering directive
children.

## A custom renderer handler is not called

Renderer handlers are selected by `node.type`, not by the Python class name.
Check the AST with `root.to_ast()` and register the exact type string:

```python
from wenmode import Wenmode

root = Wenmode().parse('**strong**')
assert root.to_ast()['children'][0]['children'][0]['type'] == 'strong'
```

For custom nodes, set a stable `type` value and register handlers from your
plugin setup function. See {ref}`custom-plugins`.

## Streaming raises StreamingUnsupportedError

Streaming cannot use rules that need document-wide deferred inline resolution,
such as reference-style links, footnotes, or abbreviations. Use the
`streaming` preset:

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)
```

If you build a custom streaming rule list, avoid `Footnote`,
`wenmode.plugins.abbr`, `Link(references=True)`, and `Image(references=True)`.
See {ref}`rule-matrix`.

## GFM syntax is not recognized

`Wenmode()` uses the `commonmark` preset. Tables, task list items,
strikethrough, footnotes, and extended autolinks require the `github` preset or
the individual standard rules.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
```

## Reference-style links stay as text

Reference-style links need `Link(references=True)` and collected reference
definitions. The `streaming` preset disables references so it can emit output
incrementally.

Use `commonmark` or `github` for full-document reference-style link support, or
use direct links in streaming responses.
