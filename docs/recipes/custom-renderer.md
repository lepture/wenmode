---
description: Write custom Wenmode renderer handlers with class-level registration or instance-level registration.
---

(recipes-custom-renderer)=
# Custom renderer

```{rst-class} lead
Create a renderer when parsed Markdown should become something other than
standard HTML.
```

---

Renderers inherit from `BaseRenderer` and dispatch handlers by node type. Use
class-level registration when a renderer type should always have a handler. Use
instance-level registration when only one configured renderer should be changed.

## Class-level handlers

Register handlers on a renderer subclass when the behavior belongs to that
renderer type. Every new instance of the subclass receives the registered
handler.

```python
from wenmode import Wenmode
from wenmode.nodes import Text
from wenmode.renderers import BaseRenderer, RenderContext


class UpperRenderer(BaseRenderer):
    pass


@UpperRenderer.register('text')
def render_text(renderer: UpperRenderer, node: Text, context: RenderContext) -> str:
    return node.value.upper()


wen = Wenmode(renderer=UpperRenderer())
source = 'Hello *there*'

text = wen.render(source)

assert text == 'HELLO THERE'
```

Use this pattern when the output format is application-specific and should be
reused across the application.

## Instance-level handlers

Register handlers on a renderer instance when the behavior should be local to
one configured `Wenmode` object.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.nodes import Text
from wenmode.renderers import RenderContext


def render_text(renderer: HTMLRenderer, node: Text, context: RenderContext) -> str:
    return renderer.escape_html(node.value.upper())


renderer = HTMLRenderer()
renderer.register_handler('text', render_text)

wen = Wenmode(renderer=renderer)
html = wen.render('Hello **there**')

assert html == '<p>HELLO <strong>THERE</strong></p>\n'
assert Wenmode().render('Hello **there**') == '<p>Hello <strong>there</strong></p>\n'
```

Use instance-level handlers for one-off presentation changes, tests, or local
application wiring. For reusable syntax extensions, package parser rules and
renderer handlers together in a plugin; see {ref}`custom-plugins`.
