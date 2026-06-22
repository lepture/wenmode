(usage)=
# Usage

```{rst-class} lead
Learn the Python and command line APIs for parsing Markdown, rendering output,
and streaming HTML chunks.
```

---

## Install

Install Wenmode from PyPI with your preferred Python package manager.

::::{tab-set}
:class: outline

:::{tab-item} {iconify}`devicon:pypi` pip

```bash
pip install wenmode
```
:::

:::{tab-item} {iconify}`material-icon-theme:uv` uv

```bash
uv add wenmode
```
:::
::::

## Core objects

Most code uses one of these shapes:

| Object | Use it when |
| --- | --- |
| `Wenmode` | You want one object that parses Markdown and renders output. |
| `Parser` | You want the AST and will render, transform, or store it yourself. |
| `HTMLRenderer`, `MarkdownRenderer`, `RSTRenderer` | You already have parsed nodes and want a specific output format. |

`Wenmode()` defaults to the `commonmark` preset and `HTMLRenderer()`. Pass a
different preset, rule list, renderer, or `positions=True` only when your
application needs that behavior.

## Quick start

`Wenmode` is the main convenience API. It owns a `Parser` and a renderer, and
uses the `commonmark` preset with `HTMLRenderer` when no options are provided.

```python
from wenmode import Wenmode

wenmode = Wenmode()
text = '''
# Hello

This is **wenmode**.
'''
expected = '''
<h1>Hello</h1>
<p>This is <strong>wenmode</strong>.</p>
'''

html = wenmode.render(text)

assert html == expected.lstrip()
```

`render()` parses the source and renders the resulting syntax tree. The source
can be a string, a synchronous text stream, or another iterable of lines.

```python
from wenmode import Wenmode

wenmode = Wenmode()

with open('README.md', encoding='utf-8') as file:
    html = wenmode.render(file)
```

## Command line

Installing Wenmode exposes the `wenmode` command. The same CLI is also available
through `python -m wenmode`, and `uvx` can run it without adding Wenmode to the
current project.

Render a Markdown file to HTML:

```bash
wenmode render README.md --preset=github
```

Run the same command without a permanent install:

```bash
uvx wenmode render README.md --preset=github
```

Read from stdin by omitting the source path or passing `-`. CLI output goes to
stdout unless you pass `-o`:

```bash
printf '# Hello\n' | wenmode render --preset=github
wenmode render README.md --format=rst -o README.rst
```

Use `ast` when you want JSON output for tooling, tests, or editor integrations:

```bash
wenmode ast README.md --preset=github --positions
python -m wenmode ast README.md --indent=2
```

The CLI supports the built-in presets: `commonmark`, `github`, and `streaming`.
It defaults to `commonmark`.

```bash
wenmode render README.md --preset=commonmark
wenmode render README.md --preset=github
```

Enable built-in plugins with `--plugin`. Repeat the option to enable multiple
plugins.

```bash
wenmode render notes.md --plugin=frontmatter --plugin=math
```

HTML output uses the same safety defaults as `HTMLRenderer()`: raw HTML nodes are
escaped, and unsafe link or image URLs are sanitized. Use `--unsafe-html` or
`--unsafe-urls` only for trusted content or content sanitized by another layer.

```bash
wenmode render trusted.md --unsafe-html --unsafe-urls
```

## Parsing

Use `parse()` when you want the AST instead of rendered output.

```python
from wenmode import Wenmode

wenmode = Wenmode()
text = 'A [link](https://example.com).'

tree = wenmode.parse(text)
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

### Source positions

Pass `positions=True` when you need source ranges for editor integration,
diagnostics, or AST-based tooling. Positions are opt-in so the default AST shape
and parser overhead stay small.

```python
from wenmode import Wenmode

wenmode = Wenmode(positions=True)
ast = wenmode.parse('A **bold**.\n').to_ast()

assert ast['children'][0]['children'][1] == {
    'type': 'strong',
    'position': {
        'start': {'line': 1, 'column': 3, 'offset': 2},
        'end': {'line': 1, 'column': 11, 'offset': 10},
    },
    'children': [
        {
            'type': 'text',
            'position': {
                'start': {'line': 1, 'column': 5, 'offset': 4},
                'end': {'line': 1, 'column': 9, 'offset': 8},
            },
            'value': 'bold',
        }
    ],
}
```

The same option is available on `Parser(commonmark, positions=True)` when you
use parser and renderer objects separately.

Parsed nodes store source ranges as 0-based offsets. `Root.to_ast()` converts
those offsets to the `line` and `column` fields shown above. If you call
`to_ast()` on a standalone node, such as a node yielded by `Parser.parse_iter()`,
the position object contains offsets only because there is no document root to
provide line-start context.

Enable positions only for tooling that needs source ranges. Leave them disabled
for ordinary HTML rendering.

## Rendering

`Wenmode()` uses `HTMLRenderer` by default. Pass a different renderer when you
want another output format.

```python
from wenmode import RSTRenderer, Wenmode

wenmode = Wenmode(renderer=RSTRenderer())
text = '# Hello'
expected = '''
Hello
=====
'''

rst = wenmode.render(text)

assert rst == expected.lstrip()
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
text = '# Hello'

root = wenmode.parse(text)
html = wenmode.render_node(root)
```

## Parser and renderer separately

Use `Parser` directly when you want parsing and rendering to be separate steps.

```python
from wenmode import HTMLRenderer, Parser
from wenmode.presets import commonmark

parser = Parser(commonmark)
text = '# Hello'

tree = parser.parse(text)

html = HTMLRenderer().render(tree)
```

Parser state is created per parse. Reference definitions, footnote definitions,
and abbreviation definitions do not leak between calls, so a parser instance can
be reused safely.

Use this split form when parsing and rendering happen in different layers of
your application, or when you need to run AST transforms before rendering.

## Streaming output

Use the `streaming` preset when you want HTML chunks without waiting for the
whole document to be parsed and rendered.

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)

text = '''
# Hello

A [link](/url).
'''

sent_chunks: list[str] = []

for chunk in wenmode.stream(text):
    sent_chunks.append(chunk)

expected = '''
<h1>Hello</h1>
<p>A <a href="/url">link</a>.</p>
'''

assert ''.join(sent_chunks) == expected.lstrip()
```

The streaming API yields rendered block output as parsing progresses. It only
works with rules that do not require deferred document-wide inline resolution.
If unsupported rules are enabled, `stream()` raises `StreamingUnsupportedError`.

`Wenmode.stream()` returns a synchronous iterator of HTML chunks. Web frameworks
that accept iterable response bodies can send those chunks directly.

See {ref}`choosing a rule preset <presets>`, {ref}`security`, and
{ref}`common integration tasks <recipes>`.

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
