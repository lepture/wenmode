(migration-markdown2)=
# Migrating from markdown2

```{rst-class} lead
Replace markdown2's Markdown-to-HTML calls and extras with Wenmode presets,
configured rules, AST helpers, and renderer options.
```

---

markdown2 exposes a compact API and optional extras. Wenmode is more explicit:
syntax is selected by presets or rules, and output is controlled by renderers.

## Simple rendering

markdown2's common API is:

```{code-block} python
:caption: markdown2

import markdown2

html = markdown2.markdown(text)
```

Use Wenmode's high-level renderer:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

html = Wenmode().render(text)
```

If you previously reused a markdown2 converter object, keep a reusable Wenmode
instance:

```{code-block} python
:caption: markdown2

import markdown2

converter = markdown2.Markdown(extras=['tables'])
html = converter.convert(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render(text)
```

## Extras mapping

markdown2 extras vary in scope. Some map directly to Wenmode rules; others need
custom rules or preprocessing.

| markdown2 extra | Wenmode replacement |
| --- | --- |
| `tables` | `github` preset or `Table` rule |
| `fenced-code-blocks` | default `commonmark` preset includes fenced code |
| `footnotes` | `github` preset or `Footnote` rule |
| `header-ids` | `AtxHeading(id_transform=True)`, `SetextHeading(id_transform=True)`, or `add_heading_ids()` |
| `strike` | `github` preset or `Strikethrough` rule |
| `code-friendly` | usually no direct migration; test the exact documents and adjust rule lists if needed |
| `smarty-pants` | run a typography transform before or after Wenmode, or add a custom renderer transform |
| `metadata` | parse front matter outside Wenmode before passing Markdown content to the parser |
| `toc`-style workflows | heading helpers plus `collect_toc()` / `render_toc_html()` |

## Tables, footnotes, and strikethrough

For the common "extras for GFM-like documents" setup:

```{code-block} python
:caption: markdown2

import markdown2

html = markdown2.markdown(text, extras=['tables', 'footnotes', 'strike'])
```

Use Wenmode's `github` preset:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

html = Wenmode(github).render(text)
```

## Heading IDs

If you used markdown2's header ID support, enable heading ID transforms:

```{code-block} python
:caption: markdown2

import markdown2

html = markdown2.markdown(text, extras=['header-ids'])
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.rules import AtxHeading, SetextHeading

wenmode = Wenmode([
    AtxHeading(id_transform=True),
    SetextHeading(id_transform=True),
])
html = wenmode.render(text)
```

For a fuller CommonMark-like dialect with heading IDs, start from
`commonmark` and replace the heading rules with configured instances.

## Raw HTML behavior

Review raw HTML behavior carefully. Wenmode's default renderer escapes raw HTML
nodes and sanitizes unsafe URLs:

```{code-block} python
:caption: markdown2

import markdown2

html = markdown2.markdown(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

html = Wenmode().render(text)
```

Use passthrough only for trusted content:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer, Wenmode

html = Wenmode(renderer=HTMLRenderer(escape=False)).render(text)
```

## AST and transformations

markdown2 is primarily an HTML converter. If you added preprocessing or
postprocessing around markdown2, consider moving that logic to Wenmode's AST:

```{code-block} python
:caption: markdown2

import markdown2

html = markdown2.markdown(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

root = Wenmode().parse(text)
payload = root.to_ast()
```

Use root transforms for document-wide state such as definitions, collected
metadata, or generated attributes.

## Checklist

- Replace `extras` with `github`, configured rules, or custom rules.
- Handle front matter or metadata outside Wenmode unless you add a custom rule.
- Rebuild heading IDs and TOC behavior with Wenmode helpers.
- Compare HTML output for raw HTML, code blocks, tables, and footnotes.
