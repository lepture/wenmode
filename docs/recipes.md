(recipes)=
# Recipes

```{rst-class} lead
Copy common integration patterns for GFM, tables of contents, heading IDs,
custom renderers, AST JSON output, and migration planning.
```

---

This page collects copyable snippets for common tasks that are one step beyond
the quick start. Use {ref}`usage` for the base API, {ref}`presets` and
{ref}`plugins` for feature selection, and {ref}`integrations` for complete
application pipelines.

## Enable GitHub-flavored Markdown

Use the `github` preset when you want tables, task list items, strikethrough,
bare URL autolinks, footnotes, and GFM disallowed HTML handling.

```python
from wenmode import Wenmode
from wenmode.presets import github

wen = Wenmode(github)
text = '''
- [x] done

| A | B |
| --- | --- |
| **x** | https://example.com |
'''

html = wen.render(text)

assert '<input checked="" disabled="" type="checkbox">' in html
assert '<table>' in html
assert '<a href="https://example.com">https://example.com</a>' in html
```

## Render a table of contents

Use the `heading_ids` plugin and register the built-in `TableOfContents`
directive renderer.

```python
from wenmode import Wenmode
from wenmode.directives import TableOfContents
from wenmode.plugins import heading_ids
from wenmode.rules import AtxHeading, LeafDirective

wen = Wenmode(
    [AtxHeading, LeafDirective],
    directives=[TableOfContents()],
    plugins=[heading_ids],
)
text = '''
::toc{min=2 max=3}

# Title

## Usage
'''

html = wen.render(text)

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

wen = Wenmode()
text = '''
# Title

## Usage
'''

root = wen.parse(text)
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
wen = Wenmode(rules)
text = '<span>text</span>'
expected = '''
<p>&lt;span&gt;text&lt;/span&gt;</p>
'''

root = wen.parse(text)
html = wen.render_node(root)

assert root.to_ast()['children'][0]['children'][0] == {
    'type': 'text',
    'value': '<span>text</span>',
}
assert html == expected.lstrip()
```

See {ref}`Security <security>` for renderer-level escaping and URL sanitization
behavior.

## Filter and stream LLM Markdown

Use `Parser.parse_iter()` with a streaming-compatible preset when an LLM response
should be rendered as HTML while it is still arriving. Filter each parsed block
before handing it to the renderer.

```python
from collections.abc import Iterable, Iterator

from wenmode import HTMLRenderer, Wenmode
from wenmode.nodes import Node
from wenmode.presets import streaming

ALLOWED_NODE_TYPES = {
    'blockquote',
    'break',
    'code',
    'delete',
    'emphasis',
    'heading',
    'inlineCode',
    'link',
    'list',
    'listItem',
    'paragraph',
    'strong',
    'table',
    'tableCell',
    'tableRow',
    'text',
    'thematicBreak',
}

wen = Wenmode(streaming, renderer=HTMLRenderer())


def filter_node(node: Node) -> Node | None:
    if node.type not in ALLOWED_NODE_TYPES:
        return None

    children = getattr(node, 'children', None)
    if isinstance(children, list):
        children[:] = [
            child
            for child in (filter_node(child) for child in children)
            if child is not None
        ]
    return node


def iter_filtered_nodes(source: str | Iterable[str]) -> Iterator[Node]:
    for node in wen.parser.parse_iter(source):
        filtered = filter_node(node)
        if filtered is not None:
            yield filtered


def render_llm_markdown(source: str | Iterable[str]) -> Iterator[str]:
    yield from wen.renderer.render_iter(iter_filtered_nodes(source))


markdown = '''
# Answer

Use **Markdown** safely.

![tracking pixel](https://example.com/pixel.png)

<script>alert(1)</script>
'''

html = ''.join(render_llm_markdown(markdown))

assert '<h1>Answer</h1>' in html
assert '<strong>Markdown</strong>' in html
assert '<img' not in html
assert '<script' not in html
```

The allowlist above removes `image` and `html` nodes. Keep the default
`HTMLRenderer()` safety settings so unsafe URLs are also removed from links that
remain allowed. If you need reference-style links, footnotes, or any other
feature that waits for the complete document, parse the full response first
instead of using `parse_iter()`.

## Generate heading IDs

Use the `heading_ids` plugin when you want Wenmode to add generated heading IDs
during parsing.

```python
from wenmode import Wenmode
from wenmode.plugins import heading_ids
from wenmode.rules import AtxHeading

wen = Wenmode([AtxHeading], plugins=[heading_ids])
text = '# Hello World'
expected = '''
<h1 id="hello-world">Hello World</h1>
'''

html = wen.render(text)

assert html == expected.lstrip()
```

For already-parsed trees, use `add_heading_ids()`.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids

text = '''
# Title

## Usage
'''

root = Wenmode().parse(text)
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

text = 'A [link](https://example.com).'

root = Wenmode().parse(text)
payload = json.dumps(root.to_ast(), ensure_ascii=False)

assert '"type": "root"' in payload
assert '"url": "https://example.com"' in payload
```

## Inspect AST nodes

Use `wenmode.ast` helpers when you want to inspect parsed node objects directly
instead of first converting them to dictionaries.

```python
from wenmode import Wenmode
from wenmode.ast import find_all, plain_text, walk
from wenmode.nodes import Heading
from wenmode.presets import github

text = '''
# Title

## Usage

A [link](https://example.com).
'''

root = Wenmode(github).parse(text)

headings = find_all(root, Heading)
links = find_all(root, 'link')
node_types = [node.type for node in walk(root)]

assert [plain_text(heading) for heading in headings] == ['Title', 'Usage']
assert links[0].url == 'https://example.com'
assert node_types[:3] == ['root', 'heading', 'text']
```

## Write a custom renderer

Renderers inherit from `BaseRenderer` and register handlers by node type. This
example turns Markdown into plain uppercase text.

Use this pattern when the output format is not HTML with a few changed tags. If
you only need to customize one HTML feature, registering a handler on an
`HTMLRenderer` subclass is usually enough.

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

## Plan a parser migration

For migrations from Mistune, Python-Markdown, markdown-it-py, markdown2, Marko,
or commonmark.py, start with the dedicated {ref}`migration` section. The guides
cover direct render-call replacements, feature mapping, HTML safety defaults,
AST migration, and custom extension migration.
