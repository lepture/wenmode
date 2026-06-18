(usage)=
# Usage

```{rst-class} lead
Learn the main APIs for parsing Markdown, rendering output, and streaming HTML
chunks.
```

---

## Quick start

`Wenmode` is the main convenience API. It owns a `Parser` and a renderer, and
uses the `commonmark` preset with `HTMLRenderer` when no options are provided.

```python
from wenmode import Wenmode

wenmode = Wenmode()
html = wenmode.render('# Hello\n\nThis is **wenmode**.')

assert html == '<h1>Hello</h1>\n<p>This is <strong>wenmode</strong>.</p>\n'
```

`render()` parses the source and renders the resulting syntax tree. The source
can be a string, a synchronous text stream, or another iterable of lines.

```python
from wenmode import Wenmode

wenmode = Wenmode()

with open('README.md', encoding='utf-8') as file:
    html = wenmode.render(file)
```

## Parsing

Use `parse()` when you want the AST instead of rendered output.

```python
from wenmode import Wenmode

wenmode = Wenmode()
tree = wenmode.parse('A [link](https://example.com).\n')
ast = tree.to_ast()

assert ast == {
    'type': 'root',
    'children': [
        {
            'type': 'paragraph',
            'children': [
                {'type': 'text', 'value': 'A '},
                {
                    'type': 'link',
                    'children': [{'type': 'text', 'value': 'link'}],
                    'url': 'https://example.com',
                },
                {'type': 'text', 'value': '.'},
            ],
        }
    ],
}
```

The returned root node is a `wenmode.nodes.Root`. Nodes are data objects; their
rendering behavior lives in renderers.

## Rendering

`Wenmode()` uses `HTMLRenderer` by default. Pass a different renderer when you
want another output format.

```python
from wenmode import RSTRenderer, Wenmode

wenmode = Wenmode(renderer=RSTRenderer())
rst = wenmode.render('# Hello\n')

assert rst == 'Hello\n=====\n'
```

Wenmode currently provides:

- `HTMLRenderer`, for HTML output.
- `MarkdownRenderer`, for serializing the AST back to Markdown.
- `RSTRenderer`, for serializing the AST to reStructuredText.
- `BaseRenderer`, a small dispatch-based base class for custom renderers.

`MarkdownRenderer` and `RSTRenderer` serialize the AST to canonical markup. They
are not source-preserving formatters; syntax details that are not represented in
the AST may be normalized or omitted.

If you already have a node, use `render_node()` to render it directly.

```python
from wenmode import Wenmode

wenmode = Wenmode()
root = wenmode.parse('# Hello\n')
html = wenmode.render_node(root)
```

## Parser and renderer separately

Use `Parser` directly when you want parsing and rendering to be separate steps.

```python
from wenmode import HTMLRenderer, Parser
from wenmode.presets import commonmark

parser = Parser(commonmark)
tree = parser.parse('# Hello\n')

html = HTMLRenderer().render(tree)
```

Parser state is created per parse. Reference definitions, footnote definitions,
and abbreviation definitions do not leak between calls, so a parser instance can
be reused safely.

## Streaming output

Use the `streaming` preset when you want HTML chunks without waiting for the
whole document to be parsed and rendered.

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)

sent_chunks: list[str] = []

for chunk in wenmode.stream('# Hello\n\nA [link](/url).\n'):
    sent_chunks.append(chunk)

assert sent_chunks == [
    '<h1>Hello</h1>\n',
    '<p>A <a href="/url">link</a>.</p>\n',
]
```

The streaming API yields rendered block output as parsing progresses. It only
works with rules that do not require deferred document-wide inline resolution.
If unsupported rules are enabled, `stream()` raises `StreamingUnsupportedError`.

`Wenmode.stream()` returns a synchronous iterator of HTML chunks. Web frameworks
that accept iterable response bodies can send those chunks directly.

See {ref}`choosing a rule preset <presets>`, {ref}`HTML and URL safety behavior
<security>`, and {ref}`common integration tasks <recipes>`.

### FastAPI

```python
from fastapi.responses import StreamingResponse
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)


async def preview(markdown: str):
    return StreamingResponse(
        wenmode.stream(markdown),
        media_type='text/html; charset=utf-8',
    )
```

### Flask

```python
from flask import Response
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)


def preview(markdown: str):
    return Response(
        wenmode.stream(markdown),
        mimetype='text/html',
    )
```

### Django

```python
from django.http import StreamingHttpResponse
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)


def preview(request):
    markdown = request.POST['markdown']
    return StreamingHttpResponse(
        wenmode.stream(markdown),
        content_type='text/html; charset=utf-8',
    )
```
