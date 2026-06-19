(migration-python-markdown)=
# Migrating from Python-Markdown

```{rst-class} lead
Move from Python-Markdown's extension-based HTML conversion to Wenmode's
explicit rule lists, AST transforms, and renderer options.
```

---

Python-Markdown focuses on Markdown-to-HTML conversion with an extension system.
Wenmode can cover the same common rendering path, but it exposes parsing and
rendering as separate steps and keeps syntax selection explicit.

## Simple HTML rendering

Python-Markdown's common entry point is:

```{code-block} python
:caption: python-markdown

import markdown

html = markdown.markdown(text)
```

Use `Wenmode().render()` for the default CommonMark-style path:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

html = Wenmode().render(text)
```

If you reused a `markdown.Markdown` instance:

```{code-block} python
:caption: python-markdown

import markdown

md = markdown.Markdown(extensions=['tables'])
html = md.reset().convert(text)
```

Use a reusable Wenmode instance instead:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render(text)
```

## Extension mapping

Python-Markdown extensions often include both parsing behavior and output
behavior. In Wenmode, those concerns are separated.

Existing code usually enables a list of extensions at conversion time:

```{code-block} python
:caption: python-markdown

import markdown

html = markdown.markdown(
    text,
    extensions=['fenced_code', 'tables', 'footnotes'],
)
```

Start with the closest Wenmode preset, then add custom rules only for features
not covered by that preset:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render(text)
```

| Python-Markdown extension | Wenmode replacement |
| --- | --- |
| `tables` | `github` preset or `Table` rule |
| `fenced_code` | default `commonmark` preset includes `FencedCode` |
| `footnotes` | `github` preset or `Footnote` rule |
| `abbr` | `wenmode.plugins.abbr`, or directive renderer for `:abbr[...]` |
| `def_list` | `wenmode.plugins.definition_list` |
| `toc` | heading IDs plus `collect_toc()` / `render_toc_html()` or `TableOfContents` directive renderer |
| `attr_list` | no global equivalent; use directives, custom rules, or renderer logic for the specific attributes you support |
| `md_in_html` | raw HTML rules plus renderer policy; sanitize externally for untrusted input |
| custom extension | custom parser rules, root transforms, directive renderers, or renderer handlers |

## Tables and GFM features

For table-heavy documents, start with the `github` preset:

```{code-block} python
:caption: python-markdown

import markdown

html = markdown.markdown(text, extensions=['tables'])
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

html = Wenmode(github).render(text)
```

The `github` preset also enables task list items, strikethrough, extended
autolinks, footnotes, and GFM disallowed HTML tag handling. If you only want
tables without the rest of GFM, build a custom rule list with `Table` and the
rules from `commonmark`.

## Table of contents migration

Python-Markdown's `toc` extension can generate heading IDs and a TOC. In
Python-Markdown, that often uses state on the `Markdown` instance:

```{code-block} python
:caption: python-markdown

import markdown

md = markdown.Markdown(extensions=['toc'])
html = md.convert(text)
toc = md.toc
```

In Wenmode, heading IDs and TOC rendering are explicit:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids
from wenmode.toc import collect_toc, render_toc_html

root = Wenmode().parse(text)
add_heading_ids(root, slugger=Slugger(), min_depth=2)

toc = collect_toc(root, min_depth=2, max_depth=3)
html = render_toc_html(toc) + HTMLRenderer().render(root)
```

For in-document TOC syntax, enable `LeafDirective` and register
`TableOfContents()`.

## HTML and sanitization

Python-Markdown extension combinations are often used with raw HTML enabled.
The old conversion call may therefore also pass HTML through:

```{code-block} python
:caption: python-markdown

import markdown

html = markdown.markdown(text)
```

Wenmode escapes raw HTML output by default:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

safe_html = Wenmode().render(text)
```

Use `HTMLRenderer(escape=False)` only for trusted or separately sanitized
content:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer, Wenmode

html = Wenmode(renderer=HTMLRenderer(escape=False)).render(text)
```

## AST workflows

Python-Markdown extensions commonly work with ElementTree output internals.
The application-facing code usually registers the extension and receives HTML:

```{code-block} python
:caption: python-markdown

import markdown

md = markdown.Markdown(extensions=['my_package.extension'])
html = md.convert(text)
```

When migrating application logic, prefer Wenmode's AST:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

root = Wenmode().parse(text)
payload = root.to_ast()
```

Use renderer handlers when the old extension only changed HTML output. Use
rules and transforms when the old extension introduced new Markdown syntax or
document-wide state.

## Checklist

- Replace `markdown.markdown(text, extensions=[...])` with a Wenmode preset or
  rule list.
- Rebuild TOC behavior explicitly with heading helpers or the TOC directive.
- Review raw HTML behavior and URL sanitization before accepting user content.
- Port extension output customization to renderer handlers.
- Port extension parser behavior to rules and transforms.
