(recipes)=
# Recipes

```{rst-class} lead
Copy common integration patterns for GFM, tables of contents, heading IDs,
custom renderers, and AST JSON output.
```

---

This page collects common tasks that are one step beyond the quick start.

## Enable GitHub-flavored Markdown

Use the `github` preset when you want tables, task list items, strikethrough,
bare URL autolinks, footnotes, and GFM disallowed HTML handling.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render(
    '- [x] done\n\n'
    '| A | B |\n'
    '| --- | --- |\n'
    '| **x** | https://example.com |\n'
)

assert '<input checked="" disabled="" type="checkbox">' in html
assert '<table>' in html
assert '<a href="https://example.com">https://example.com</a>' in html
```

## Render a table of contents

Use heading rules with `id_transform=True` and register the built-in
`TableOfContents` directive renderer.

```python
from wenmode import Wenmode
from wenmode.directives import TableOfContents
from wenmode.rules import AtxHeading, LeafDirective

wenmode = Wenmode(
    [AtxHeading(id_transform=True), LeafDirective],
    directives=[TableOfContents()],
)

html = wenmode.render('::toc{min=2 max=3}\n\n# Title\n\n## Usage\n')

assert '<nav aria-label="Table of contents" class="toc">' in html
assert '<a href="#usage">Usage</a>' in html
assert '<h2 id="usage">Usage</h2>' in html
```

You can also build a table of contents manually when you want to place or style
it outside the Markdown document.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids
from wenmode.toc import collect_toc, render_toc_html

wenmode = Wenmode()
root = wenmode.parse('# Title\n\n## Usage\n')
add_heading_ids(root, slugger=Slugger(), min_depth=2)

toc = collect_toc(root, min_depth=2, max_depth=3)
html = render_toc_html(toc) + HTMLRenderer().render(root)

assert '<a href="#usage">Usage</a>' in html
```

## Disable raw HTML syntax

The default HTML renderer escapes raw HTML output. If you also want raw HTML
syntax to stay as plain text in the AST, use a rule list without `HtmlBlock` and
`RawHtml`.

```python
from wenmode import Wenmode
from wenmode.presets import commonmark
from wenmode.rules import HtmlBlock, RawHtml

rules = [rule for rule in commonmark if rule not in {HtmlBlock, RawHtml}]
wenmode = Wenmode(rules)

root = wenmode.parse('<span>text</span>\n')
html = wenmode.render_node(root)

assert root.to_ast()['children'][0]['children'][0] == {
    'type': 'text',
    'value': '<span>text</span>',
}
assert html == '<p>&lt;span&gt;text&lt;/span&gt;</p>\n'
```

See {ref}`Security <security>` for renderer-level escaping and URL sanitization
behavior.

## Generate heading IDs

Pass `id_transform=True` to heading rules when you want Wenmode to add generated
heading IDs during parsing.

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading

wenmode = Wenmode([AtxHeading(id_transform=True)])
html = wenmode.render('# Hello World\n')

assert html == '<h1 id="hello-world">Hello World</h1>\n'
```

For already-parsed trees, use `add_heading_ids()`.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids

root = Wenmode().parse('# Title\n\n## Usage\n')
add_heading_ids(root, slugger=Slugger(), min_depth=2)

html = HTMLRenderer().render(root)
assert '<h1>Title</h1>' in html
assert '<h2 id="usage">Usage</h2>' in html
```

## Convert the AST to JSON

`Node.to_ast()` returns plain Python dictionaries and lists, so you can serialize
the parsed tree with the standard `json` module.

```python
import json

from wenmode import Wenmode

root = Wenmode().parse('A [link](https://example.com).\n')
payload = json.dumps(root.to_ast(), ensure_ascii=False)

assert '"type": "root"' in payload
assert '"url": "https://example.com"' in payload
```

## Write a custom renderer

Renderers inherit from `BaseRenderer` and register handlers by node type. This
example turns Markdown into plain uppercase text.

```python
from wenmode import Wenmode
from wenmode.nodes import Text
from wenmode.renderers import BaseRenderer, RenderContext


class UpperRenderer(BaseRenderer):
    pass


@UpperRenderer.register('text')
def render_text(renderer: UpperRenderer, node: Text, context: RenderContext) -> str:
    return node.value.upper()


wenmode = Wenmode(renderer=UpperRenderer())
text = wenmode.render('Hello *there*\n')

assert text == 'HELLO THERE'
```

## Migrate simple Mistune usage

For the common "Markdown string to HTML string" path, replace Mistune's HTML
helper with `Wenmode().render()`.

```python
from wenmode import Wenmode

markdown = '# Hello\n\nThis is **wenmode**.'

# Mistune:
# html = mistune.html(markdown)

# Wenmode:
html = Wenmode().render(markdown)

assert html == '<h1>Hello</h1>\n<p>This is <strong>wenmode</strong>.</p>\n'
```

Mistune plugins do not map one-to-one to Wenmode APIs. In Wenmode, choose a
preset for the baseline dialect, add or remove rules for syntax, and register
directive renderers or custom renderers for output behavior.
