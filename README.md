# Wenmode

Wenmode is a composable Markdown toolkit. The top-level `Wenmode` class combines
a parser and a renderer: by default it parses CommonMark-style Markdown and
renders HTML.

Rules are opt-in and composable. You can use the default `commonmark` preset,
choose a different rule set, or register rules and directive renderers at
runtime.

## Quick Start

```python
from wenmode import Wenmode

wenmode = Wenmode()

html = wenmode.render('# Hello\n\nThis is **wenmode**.')
```

`render()` parses source text and renders it. Use `parse()` when you need the
syntax tree:

```python
tree = wenmode.parse('A [link](https://example.com).\n')
ast = tree.to_ast()
```

`parse()` also accepts synchronous text streams and other iterables of lines:

```python
with open('README.md', encoding='utf-8') as f:
    tree = wenmode.parse(f)
```

## Rendering

`Wenmode()` uses `HTMLRenderer` by default. Pass a renderer when you want a
different output format:

```python
from wenmode import MarkdownRenderer, Wenmode

wenmode = Wenmode(renderer=MarkdownRenderer())

markdown = wenmode.render('# Hello\n')
```

Wenmode currently provides:

- `HTMLRenderer`, for HTML output.
- `MarkdownRenderer`, for serializing the AST back to Markdown.
- `BaseRenderer`, a small text-rendering base class for custom renderers.

```python
from wenmode.renderers import BaseRenderer


class PlainTextRenderer(BaseRenderer):
    pass
```

`BaseRenderer` falls back to rendering child nodes or literal `value` fields,
which makes it a useful starting point for simple text renderers.

## Rules

The default `Wenmode()` parser uses the `commonmark` preset. Pass an explicit
rule list when you want to override the defaults:

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading, FencedCode, Image, InlineCode, Link

wenmode = Wenmode([AtxHeading, FencedCode, Link, Image, InlineCode])

assert wenmode.render('# h1\n\nhi `code` **strong**') == (
    '<h1>h1</h1>\n<p>hi <code>code</code> **strong**</p>\n'
)
```

Because `Emphasis` is not enabled above, `**strong**` stays as text. Enabling
`Emphasis` supports both emphasis and strong emphasis.

Pass `[]` when you want no rules enabled:

```python
wenmode = Wenmode([])
```

Rules can also be registered after construction:

```python
from wenmode import Wenmode
from wenmode.rules import ContainerDirective

wenmode = Wenmode()
wenmode.register_rule(ContainerDirective)
```

Rules are instances internally and are exposed through `wenmode.parser.rules` as
a `{rule_name: rule}` dictionary. This lets rules consult other enabled rules
without assuming a fixed preset.

## Directives

Directive syntax is enabled by parser rules, while directive output is handled by
renderer plugins:

```python
from wenmode import Wenmode
from wenmode.directives import Admonition
from wenmode.rules import ContainerDirective

wenmode = Wenmode()
wenmode.register_rule(ContainerDirective)
wenmode.register_directive_renderer(Admonition())

html = wenmode.render(':::note[Title]\nBody.\n:::\n')
```

`register_directive_renderer()` requires an `HTMLRenderer`, because directive
renderers produce HTML.

## Parser

Use `Parser` directly when you only need an AST and want to choose rendering
separately:

```python
from wenmode import HTMLRenderer, Parser
from wenmode.presets import commonmark

parser = Parser(commonmark)
tree = parser.parse('# Hello\n')

html = HTMLRenderer().render(tree)
```

`Parser` supports the same rule registration methods as `Wenmode`:

```python
from wenmode import Parser
from wenmode.rules import AtxHeading

parser = Parser([])
parser.register_rule(AtxHeading)
```

Parser state is per parse. Reference definitions and footnote definitions do not
leak between calls, so a parser instance can be reused safely.

## Presets

`commonmark` enables the CommonMark-oriented rule set:

```python
from wenmode import Wenmode
from wenmode.presets import commonmark

wenmode = Wenmode(commonmark)
```

The preset includes headings, block quotes, lists, code blocks, HTML blocks,
links, images, inline code, emphasis, escapes, character references, hard
breaks, and autolinks.

The `github` preset adds GitHub-flavored features such as tables,
strikethrough, task lists, extended autolinks, and footnotes:

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
```

## Streaming Output

Use the `streaming` preset when you want to render HTML chunks without waiting
for the entire document to be parsed and rendered:

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)

for chunk in wenmode.stream('# Hello\n\nA [link](/url).\n'):
    send(chunk)
```

The `streaming` preset uses the CommonMark-oriented rules, but disables
reference-style links and images. Direct links and images still work, while
`[label]`, `[label][id]`, and `![label]` stay as text.

For FastAPI, pass the synchronous iterator to `StreamingResponse`:

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

## Nodes

Node classes live in `wenmode.nodes`. Their `type` values follow mdast naming:

- `root`
- `paragraph`
- `heading`
- `blockquote`
- `list`
- `listItem`
- `code`
- `thematicBreak`
- `html`
- `text`
- `inlineCode`
- `strong`
- `emphasis`
- `link`
- `image`
- `break`
- `footnoteReference`
- `footnoteDefinition`

Nodes are data objects. Rendering behavior belongs to renderers, so the same
AST can be rendered to HTML, Markdown, or another text format.

Use `to_ast()` when you need a plain dictionary representation:

```python
{
    'type': 'root',
    'children': [
        {
            'type': 'heading',
            'depth': 1,
            'children': [{'type': 'text', 'value': 'Hello'}],
        },
    ],
}
```

## References And Footnotes

Reference extraction only runs when an enabled rule registers the reference
transform. `Link` and `Image` do this by default.

Footnote definitions are collected by the footnote transform. To enable
footnotes without the full GitHub preset, include `Footnote` in your rule list.

```python
from wenmode import Wenmode
from wenmode.rules import Footnote

wenmode = Wenmode([Footnote])
html = wenmode.render('A note[^one].\n\n[^one]: Footnote text.\n')
```

## Table Of Contents

Use `add_heading_ids` to assign stable heading anchors, then collect and render
a table of contents from the AST:

```python
from wenmode import HTMLRenderer, Parser
from wenmode.headings import Slugger, add_heading_ids
from wenmode.presets import commonmark
from wenmode.toc import collect_toc, render_toc_html

root = Parser(commonmark).parse(markdown)
add_heading_ids(root, slugger=Slugger(), min_depth=2)

toc = collect_toc(root, min_depth=2, max_depth=3)
html = render_toc_html(toc) + HTMLRenderer().render(root)
```

You can also render an in-document table of contents with the `toc` directive:

```python
from wenmode import HTMLRenderer, Parser
from wenmode.directives import TableOfContents
from wenmode.presets import commonmark
from wenmode.rules import AtxHeading, LeafDirective, SetextHeading

rules = list(commonmark)
rules[rules.index(AtxHeading)] = AtxHeading(id_transform=True)
rules[rules.index(SetextHeading)] = SetextHeading(id_transform=True)
rules.append(LeafDirective)

root = Parser(rules).parse('::toc{min=2 max=3}\n\n## Intro\n')
html = HTMLRenderer(directives=[TableOfContents()]).render(root)
```

## Rule Layout

The implementation is split by rule type:

- `wenmode.rules.blocks` contains block rules such as headings, block quotes,
  lists, and fenced code.
- `wenmode.rules.inlines` contains inline rules such as links, images, inline
  code, emphasis, escapes, and raw HTML.
- `wenmode.rules.references` contains shared reference-definition extraction.
- `wenmode.rules.footnotes` contains footnote references and definitions.

This keeps complex rules, such as lists, in their own modules while preserving a
single public import surface through `wenmode.rules`.

## Development

```bash
uv run --group test pytest -q
uv run ruff check .
uv run mypy
```
