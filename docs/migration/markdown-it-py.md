(migration-markdown-it-py)=
# Migrating from markdown-it-py

```{rst-class} lead
Move markdown-it-py render calls, presets, token workflows, and plugins to
Wenmode presets, nodes, rules, and renderer handlers.
```

---

markdown-it-py is configurable through presets, options, plugins, and rule
chains. Wenmode has a similar goal of explicit composition, but uses Python node
objects rather than markdown-it token streams.

## Simple rendering

markdown-it-py rendering usually starts with a `MarkdownIt` instance:

```{code-block} python
:caption: markdown-it-py

from markdown_it import MarkdownIt

md = MarkdownIt('commonmark')
html = md.render(text)
```

The closest Wenmode replacement is:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

html = Wenmode().render(text)
```

For GFM-like behavior, use Wenmode's `github` preset:

```{code-block} python
:caption: markdown-it-py

from markdown_it import MarkdownIt

md = MarkdownIt('gfm-like')
html = md.render(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

html = Wenmode(github).render(text)
```

## Preset and option mapping

| markdown-it-py behavior | Wenmode replacement |
| --- | --- |
| `MarkdownIt('commonmark')` | `Wenmode()` or `Wenmode(commonmark)` |
| `MarkdownIt('gfm-like')` | `Wenmode(github)` for GFM syntax |
| `.enable('table')` | `Table` rule or `github` preset |
| `.enable('strikethrough')` | `Strikethrough` rule or `github` preset |
| `html=True` | raw HTML rules plus `HTMLRenderer(escape=False)` for trusted input |
| `linkify` | `ExtendedAutolink` rule or `github` preset |
| disabled rules | custom Wenmode rule list that omits those rules |

## Token workflows

If your application consumed markdown-it tokens:

```{code-block} python
:caption: markdown-it-py

from markdown_it import MarkdownIt

tokens = MarkdownIt('commonmark').parse(text)
```

Migrate to Wenmode nodes:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

root = Wenmode().parse(text)
payload = root.to_ast()
```

The data model changes from a flat token stream with nesting markers to a tree
of node objects. For document analysis, this usually simplifies traversal:
walk `root.children` and descend through nodes that have `children`.

## Plugin migration

markdown-it-py plugins commonly add syntax rules and rendering rules together.
In Wenmode, split that work:

- parser syntax becomes `InlineRule`, `BlockRule`, or `ContinueRule`,
- document-wide state becomes a root transform with `StateKey`,
- HTML output becomes an `HTMLRenderer.register()` handler,
- Markdown or RST output becomes handlers on `MarkdownRenderer` or
  `RSTRenderer`,
- directive-like syntax can use directive rules plus directive renderers.

The old integration often attaches a plugin to a `MarkdownIt` instance:

```{code-block} python
:caption: markdown-it-py

from markdown_it import MarkdownIt
from my_package import my_plugin

md = MarkdownIt('commonmark').use(my_plugin)
html = md.render(text)
```

In Wenmode, package parser rules and renderer handlers in a plugin:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from my_package.wenmode_plugins import my_plugin

wenmode = Wenmode(plugins=[my_plugin])
html = wenmode.render(text)
```

See {ref}`custom-plugins` for custom plugin creation.

## Renderer migration

markdown-it-py render rules attach output callbacks to token types:

```{code-block} python
:caption: markdown-it-py

from markdown_it import MarkdownIt


def render_text(renderer, tokens, index, options, env):
    return tokens[index].content


md = MarkdownIt('commonmark')
md.add_render_rule('text', render_text)
html = md.render(text)
```

Wenmode renderer handlers attach output callbacks to node types:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer
from wenmode.nodes import Text
from wenmode.renderers import RenderContext


@HTMLRenderer.register('text')
def render_text(renderer: HTMLRenderer, node: Text, context: RenderContext) -> str:
    return renderer.escape_html(node.value)
```

## Raw HTML and security

markdown-it-py applications often use the `html` option to allow raw HTML. In
markdown-it-py this is parser configuration:

```{code-block} python
:caption: markdown-it-py

from markdown_it import MarkdownIt

md = MarkdownIt('commonmark', {'html': True})
html = md.render(text)
```

In Wenmode, raw HTML can be parsed while still being escaped by the default HTML
renderer. To pass raw HTML through, configure the renderer explicitly:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer, Wenmode

html = Wenmode(renderer=HTMLRenderer(escape=False)).render(text)
```

Keep the default renderer for untrusted user-authored Markdown.

## Streaming

If your markdown-it-py integration rendered whole documents but your application
would benefit from incremental responses, Wenmode can use a streaming preset:

```{code-block} python
:caption: markdown-it-py

from markdown_it import MarkdownIt

html = MarkdownIt('commonmark').render(text)
send(html)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import streaming

for chunk in Wenmode(streaming).stream(text):
    send(chunk)
```

The streaming preset disables reference-style links, reference-style images,
footnotes, and other features that require document-wide deferred inline
resolution.

## Checklist

- Choose `commonmark`, `github`, or `streaming`.
- Convert token-stream code to node traversal or `to_ast()`.
- Split plugins into parser rules, transforms, and renderer handlers.
- Review raw HTML and linkification behavior.
- Compare rendered HTML for tables, strikethrough, task lists, and autolinks.
