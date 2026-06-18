(migration-marko)=
# Migrating from Marko

```{rst-class} lead
Move Marko conversion, AST traversal, renderer overrides, and extensions to
Wenmode parser rules, nodes, transforms, and renderer handlers.
```

---

Marko and Wenmode both expose parser and renderer concepts, so migration is
usually straightforward at the architecture level. The main work is adapting
node classes, extension hooks, and renderer methods.

## Simple rendering

Marko's direct conversion path is:

```{code-block} python
:caption: marko

import marko

html = marko.convert(text)
```

Use Wenmode:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

html = Wenmode().render(text)
```

If you use a configured Marko Markdown object:

```{code-block} python
:caption: marko

import marko

markdown = marko.Markdown(extensions=['footnote'])
html = markdown.convert(text)
```

Use a configured Wenmode instance:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render(text)
```

## AST migration

Marko's AST classes are not the same as Wenmode nodes. Replace Marko-specific
node checks with Wenmode node types:

```{code-block} python
:caption: marko

import marko

markdown = marko.Markdown()
root = markdown.parse(text)
```

```{code-block} python
:caption: wenmode

from wenmode import Wenmode

root = Wenmode().parse(text)
```

Use `root.to_ast()` when you need serializable dictionaries:

```{code-block} python
:caption: wenmode

payload = root.to_ast()
```

Wenmode's documented node types are listed in {ref}`reference`.

## Extension mapping

Marko extensions typically define parser elements and renderer behavior.
In Wenmode, split extensions into:

- `InlineRule` for inline syntax,
- `BlockRule` for block syntax,
- `ContinueRule` for paragraph continuations,
- root transforms for document-wide state,
- renderer handlers for HTML, Markdown, RST, or custom output.

If a Marko extension introduced a new AST element, create a custom Wenmode node
and register renderers for it. See {ref}`custom-rules`.

## Renderer migration

Marko renderers usually override methods on renderer classes:

```{code-block} python
:caption: marko

from marko import Markdown
from marko.html_renderer import HTMLRenderer


class MyRenderer(HTMLRenderer):
    def render_paragraph(self, element):
        return f'<p class="lead">{self.render_children(element)}</p>\n'


markdown = Markdown(renderer=MyRenderer)
html = markdown.convert(text)
```

Wenmode renderers register handlers by node type:

```{code-block} python
:caption: wenmode

from wenmode import HTMLRenderer
from wenmode.nodes import Paragraph
from wenmode.renderers import RenderContext


@HTMLRenderer.register('paragraph')
def render_paragraph(
    renderer: HTMLRenderer,
    node: Paragraph,
    context: RenderContext,
) -> str:
    body = renderer.render_children(node.children, context)
    return f'<p class="lead">{body}</p>\n'
```

For application-specific output, subclass `BaseRenderer` and register handlers
on the subclass so the global `HTMLRenderer` behavior stays unchanged.

## GFM and extras

If your Marko setup enabled GFM-like extensions:

```{code-block} python
:caption: marko

from marko.ext.gfm import gfm

html = gfm(text)
```

Start with Wenmode's `github` preset:

```{code-block} python
:caption: wenmode

from wenmode import Wenmode
from wenmode.presets import github

html = Wenmode(github).render(text)
```

For a smaller dialect, pass only the rule classes or configured rule instances
you need.

## Checklist

- Replace `marko.convert(text)` with `Wenmode().render(text)`.
- Replace Marko AST traversal with Wenmode node traversal or `to_ast()`.
- Split Marko extensions into rules, transforms, and renderer handlers.
- Review renderer behavior for custom nodes.
- Decide whether you need `commonmark`, `github`, `streaming`, or a custom rule
  list.
