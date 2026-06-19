(migration-commonmark-py)=
# Migrating from commonmark.py

```{rst-class} lead
Move CommonMark-only rendering and AST workflows from commonmark.py to
Wenmode's CommonMark-style preset, optional GFM rules, and plugins.
```

---

commonmark.py targets the CommonMark specification. Wenmode's default
`Wenmode()` path is also CommonMark-oriented, while making it possible to add
GFM and Wenmode plugins later.

## Simple rendering

commonmark.py commonly renders HTML with:

```{code-block} python
:caption: commonmark.py

import commonmark

html = commonmark.commonmark(text)
```

Use Wenmode:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

html = Wenmode().render(text)
```

## Parser and renderer separately

If your commonmark.py integration separated parsing and rendering, mirror that
shape with `Parser` and `HTMLRenderer`.

```{code-block} python
:caption: commonmark.py

import commonmark

parser = commonmark.Parser()
renderer = commonmark.HtmlRenderer()

root = parser.parse(text)
html = renderer.render(root)
```

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer, Parser
from wenmode.presets import commonmark

parser = Parser(commonmark)
root = parser.parse(text)
html = HTMLRenderer().render(root)
```

## AST migration

commonmark.py AST objects and Wenmode nodes are different. Migrate to
`to_ast()` when you need plain data.

```{code-block} python
:caption: commonmark.py

import commonmark

root = commonmark.Parser().parse(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

root = Wenmode().parse(text)
payload = root.to_ast()
```

Wenmode uses mdast-style node names where possible, so downstream tools that
already understand `root`, `paragraph`, `heading`, `text`, `link`, `image`, and
`code` shapes are usually easier to adapt than code tied to commonmark.py's
node classes.

## Adding features after migration

Once the CommonMark path is migrated, you can opt into additional syntax:

```{code-block} python
:caption: commonmark.py

import commonmark

html = commonmark.commonmark(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

html = Wenmode(github).render(text)
```

Use `github` for tables, task list items, strikethrough, extended autolinks,
footnotes, and GFM disallowed HTML tag handling. Use custom rule lists for
smaller dialects.

## Raw HTML behavior

Review raw HTML output. Wenmode parses raw HTML syntax in the default preset,
but the default `HTMLRenderer()` escapes raw HTML nodes. If your commonmark.py
integration expected raw HTML passthrough for trusted input, configure that
explicitly:

```{code-block} python
:caption: commonmark.py

import commonmark

html = commonmark.commonmark(text)
```

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer, Wenmode

html = Wenmode(renderer=HTMLRenderer(escape=False)).render(text)
```

Keep the default renderer for untrusted user-authored Markdown.

## Checklist

- Replace `commonmark.commonmark(text)` with `Wenmode().render(text)`.
- Replace commonmark.py AST traversal with Wenmode node traversal or `to_ast()`.
- Review raw HTML passthrough assumptions.
- Add `github`, built-in plugins, or custom plugins only after the CommonMark migration is stable.
