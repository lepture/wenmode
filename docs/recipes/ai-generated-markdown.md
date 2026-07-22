---
description: Parse, filter, and stream AI-generated Markdown safely in Python with Wenmode's AST, explicit rules, and safer HTML renderer defaults.
---

(ai-markdown)=
# AI-generated Markdown

```{rst-class} lead
Parse, filter, and stream Markdown from LLMs before rendering it into your
application.
```

---

LLMs often return Markdown because it is compact, readable, and easy to display.
Do not render generated Markdown directly in a production application. You may
need to:

- restrict the allowed Markdown syntax;
- remove images, raw HTML, or unknown extension nodes;
- validate link and image URLs;
- stream a preview before the complete answer is available;
- store AST data for search, citations, or analytics.

Wenmode supports this workflow because parsing, AST inspection, filtering, and
rendering are separate steps.

## Choose a rule set

Use the `streaming` preset to render the response as tokens arrive. It supports
common block and inline syntax, tables,
strikethrough, direct links, and direct images, but disables features that need
the complete document, such as reference-style links and footnotes.

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wen = Wenmode(streaming)
```

If the answer uses reference-style links, footnotes, or document-wide
transforms, parse the complete answer with `commonmark`, `github`, or a custom
rule list before you render it.

## Filter nodes before rendering

Use `Parser.parse_iter()` with a streaming-compatible preset when each completed
top-level block can be filtered and rendered independently.

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
    'root',
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


def render_ai_markdown(source: str | Iterable[str]) -> Iterator[str]:
    yield from wen.renderer.render_iter(iter_filtered_nodes(source))
```

The allowlist above removes images and raw HTML because `image` and `html` are
not included in `ALLOWED_NODE_TYPES`.

## Render streamed output

The function accepts a string, a line iterator, or another iterable that yields
Markdown chunks.

```python
markdown = '''
# Answer

Use **Markdown** safely.

![tracking pixel](https://example.com/pixel.png)

<script>alert(1)</script>
'''

html = ''.join(render_ai_markdown(markdown))

assert '<h1>Answer</h1>' in html
assert '<strong>Markdown</strong>' in html
assert '<img' not in html
assert '<script' not in html
```

Keep the default `HTMLRenderer()` safety settings. The renderer removes unsafe
URLs from links that pass the node filter. Node filtering and renderer safety
have different roles: filtering selects the allowed Markdown constructs, while
the renderer converts the remaining nodes to HTML.

## Parse the full answer when needed

Some Markdown features require the complete document. For those cases, parse the
whole generated answer, filter or transform the root node, then render it.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.presets import github

wen = Wenmode(github, renderer=HTMLRenderer())
markdown = '''
# Answer

A [reference][id].

[id]: https://example.com
'''

root = wen.parse(markdown)
filtered = filter_node(root)
html = wen.render_node(filtered) if filtered is not None else ''
```

Use the full-document path when you need footnotes, reference-style links,
heading ID transforms, table-of-contents generation, or AST JSON for storage
and indexing.

## Store structured output

If another service needs to inspect the generated answer, serialize the AST
instead of scraping rendered HTML.

```python
import json

from wenmode import Wenmode

root = Wenmode().parse('A [link](https://example.com).')
payload = json.dumps(root.to_ast(), ensure_ascii=False)

assert '"type": "root"' in payload
assert '"url": "https://example.com"' in payload
```

For production renderer policy, read {ref}`security`.
