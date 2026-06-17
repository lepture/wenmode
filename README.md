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

tree = wenmode.parse('# Hello\n\nThis is **wenmode**.')
html = wenmode.render(tree)
ast = tree.to_ast()
```

`parse()` returns a `Root` node from `wenmode.nodes`. `render()` accepts a node,
so parsing and rendering stay explicit:

```python
tree = wenmode.parse('A [link](https://example.com).\n')
html = wenmode.render(tree)
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
tree = wenmode.parse('# Hello\n')

markdown = wenmode.render(tree)
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
tree = wenmode.parse('# h1\n\nhi `code` **strong**')

assert wenmode.render(tree) == '<h1>h1</h1>\n<p>hi <code>code</code> **strong**</p>\n'
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

tree = wenmode.parse(':::note[Title]\nBody.\n:::\n')
html = wenmode.render(tree)
```

`register_directive_renderer()` requires an `HTMLRenderer`, because directive
renderers produce HTML.

## Parser

Use `Parser` directly when you only need an AST and want to choose rendering
separately:

```python
from wenmode import HTMLRenderer, Parser, commonmark

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
from wenmode import Wenmode, commonmark

wenmode = Wenmode(commonmark)
```

The preset includes headings, block quotes, lists, code blocks, HTML blocks,
links, images, inline code, emphasis, escapes, character references, hard
breaks, and autolinks.

The `github` preset adds GitHub-flavored features such as tables,
strikethrough, task lists, extended autolinks, and footnotes:

```python
from wenmode import Wenmode, github

wenmode = Wenmode(github)
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

Reference extraction only runs when an enabled rule declares that it consumes
references. `Link` and `Image` do this today.

Footnote definitions are kept in parse state like link references. To enable
footnotes without the full GitHub preset, include `Footnote` in your rule list.

```python
from wenmode import Wenmode
from wenmode.rules import Footnote

wenmode = Wenmode([Footnote])
tree = wenmode.parse('A note[^one].\n\n[^one]: Footnote text.\n')
html = wenmode.render(tree)
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
