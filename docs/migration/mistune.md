(migration-mistune)=
# Migrating from Mistune

```{rst-class} lead
Replace Mistune helpers, plugins, AST usage, and renderer subclasses with
Wenmode presets, explicit rules, node transforms, and renderer handlers.
```

---

Mistune and Wenmode share design DNA, but their extension models are different.
Mistune centers on Markdown instances, plugins, and renderers. Wenmode centers
on explicit parser rules, mdast-compatible nodes, document transforms, and
renderer dispatch.

## Simple HTML rendering

Mistune's convenience helper converts Markdown directly to HTML:

```{code-block} python
:caption: mistune

import mistune

html = mistune.html(text)
```

The closest Wenmode replacement is:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

html = Wenmode().render(text)
```

## Reusable parser instances

Mistune applications often create a reusable Markdown instance:

```{code-block} python
:caption: mistune

import mistune

markdown = mistune.create_markdown(renderer='html', plugins=['table'])
html = markdown(text)
```

In Wenmode, keep a reusable `Wenmode` object:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render(text)
```

Parser state is created per parse, so definitions, footnotes, abbreviations,
and deferred inline queues do not leak between calls.

## Plugin and GFM setup

Choose `github` when your Mistune use relied on GFM-like features such as
tables, task list items, strikethrough, extended autolinks, or footnotes:

```{code-block} python
:caption: mistune

import mistune

markdown = mistune.create_markdown(
    plugins=['table', 'strikethrough', 'footnotes', 'url'],
)
html = markdown(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render(text)
```

For a smaller dialect, start from `commonmark` and add only the Wenmode rules
that correspond to the Mistune plugins you actually used.

## HTML safety behavior

Mistune configurations are often used as direct HTML filters. When migrating,
check whether raw HTML was supposed to pass through.

If the old integration intentionally allowed raw HTML, it often looked like
this:

```{code-block} python
:caption: mistune

import mistune

markdown = mistune.create_markdown(escape=False)
html = markdown(text)
```

Use Wenmode raw HTML passthrough only for trusted or separately sanitized input:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer, Wenmode

wenmode = Wenmode(renderer=HTMLRenderer(escape=False))
html = wenmode.render(text)
```

Wenmode's default `HTMLRenderer()` escapes raw HTML and sanitizes unsafe URLs, so
keep the default renderer for user-authored content.

To keep raw HTML syntax as text in the AST, remove `HtmlBlock` and `RawHtml`
from the rule list instead of relying only on renderer escaping.

## Plugin mapping

Mistune plugins do not map one-to-one to Wenmode APIs. Use this table as a
starting point:

| Mistune behavior | Wenmode replacement |
| --- | --- |
| `table` | `github` preset or `Table` rule |
| `strikethrough` | `github` preset or `Strikethrough` rule |
| `footnotes` | `github` preset or `Footnote` rule |
| `url` / bare autolinks | `github` preset or `ExtendedAutolink` rule |
| custom inline plugin | custom `InlineRule` |
| custom block plugin | custom `BlockRule` or `ContinueRule` |
| plugin state | `StateKey` and `BlockState.store` |
| renderer plugin | renderer handler registered with `HTMLRenderer.register()` or another renderer class |

## AST migration

If you used Mistune's AST renderer:

```{code-block} python
:caption: mistune

import mistune

markdown = mistune.create_markdown(renderer='ast')
tokens = markdown(text)
```

Migrate code to Wenmode nodes:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

root = Wenmode().parse(text)
payload = root.to_ast()
```

Wenmode's `to_ast()` output uses mdast-style dictionaries where possible:
`root`, `paragraph`, `heading`, `text`, `link`, `image`, `code`, `html`, and
extension node types such as `table`, `footnoteReference`, and directives.

For code that previously walked Mistune tokens, prefer direct node traversal
when you need Python objects, or `root.to_ast()` when you need serializable data.

## Renderer migration

Mistune custom renderers:

```{code-block} python
:caption: mistune

import mistune


class MyRenderer(mistune.HTMLRenderer):
    def text(self, text: str) -> str:
        return mistune.escape(text)


markdown = mistune.create_markdown(renderer=MyRenderer())
html = markdown(text)
```

Become Wenmode renderer handlers:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer
from wenmode.nodes import Text
from wenmode.renderers import RenderContext


@HTMLRenderer.register('text')
def render_text(renderer: HTMLRenderer, node: Text, context: RenderContext) -> str:
    return renderer.escape_html(node.value)
```

For custom node types, define the node in a Wenmode plugin and register handlers
for every output format you support. See {ref}`custom-plugins` for a complete
custom plugin example.

## Checklist

- Pick `commonmark` or `github` before porting individual plugins.
- Decide whether raw HTML should be escaped or passed through.
- Replace Mistune plugins with built-in Wenmode plugins, custom plugins,
  directive renderers, or renderer handlers.
- Compare generated HTML for real documents, especially tables, footnotes,
  raw HTML, and autolinks.
- Update tests that asserted Mistune token shapes to assert Wenmode nodes or
  `to_ast()` dictionaries instead.
