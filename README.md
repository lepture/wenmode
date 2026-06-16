# Wenmode

Wenmode is a composable Markdown parser. Instead of enabling one fixed Markdown
grammar, you choose the block and inline rules that should participate in a
parse. Rules that are not enabled are treated as normal text whenever possible.

The produced syntax tree uses mdast-style node names, and output is handled by
renderers such as `HTMLRenderer` and `MarkdownRenderer`.

## Quick Start

```python
from wenmode import COMMON_MARK, HTMLRenderer, MarkdownRenderer, Wenmode

parser = Wenmode(COMMON_MARK)
tree = parser.parse('# Hello\n\nThis is **wenmode**.')

html = HTMLRenderer().render(tree)
markdown = MarkdownRenderer().render(tree)
ast = tree.to_ast()
```

`tree` is a `Root` node from `wenmode.nodes`. Use `to_ast()` when you need a
plain dictionary representation:

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

## Composable Rules

Rules live in `wenmode.rules`:

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.rules import AtxHeading, FencedCode, Image, InlineCode, Link

parser = Wenmode([AtxHeading, FencedCode, Link, Image, InlineCode])
tree = parser.parse('# h1\n\nhi `code` **strong**')

assert HTMLRenderer().render(tree) == '<h1>h1</h1>\n<p>hi <code>code</code> **strong**</p>\n'
```

Because `Emphasis` is not enabled above, `**strong**` stays as text. Enabling
`Emphasis` supports both emphasis and strong emphasis.

Rules are instances internally and are exposed through `parser.rules` as a
`{rule_name: rule}` dictionary. This lets rules consult other enabled rules
without assuming a fixed preset.

## Presets

`COMMON_MARK` enables the CommonMark-oriented rule set:

```python
from wenmode import COMMON_MARK, Wenmode

parser = Wenmode(COMMON_MARK)
```

The preset includes headings, block quotes, lists, code blocks, HTML blocks,
links, images, inline code, emphasis, escapes, character references, hard
breaks, and autolinks.

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

Nodes are data objects. Rendering behavior belongs to renderers, so the same
AST can be rendered to HTML, Markdown, or another text format.

## Renderers

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

## References

Reference definitions are kept in parse state, not on the parser. A `Wenmode`
instance can be reused safely across parses:

```python
from wenmode import Wenmode
from wenmode.rules import Link

parser = Wenmode([Link])

parser.parse('[x]: /url\n\n[x]\n')
parser.parse('[x]\n')  # no reference leaks from the previous parse
```

Reference extraction only runs when an enabled rule declares that it consumes
references. `Link` and `Image` do this today; future extensions such as
footnotes can opt in the same way.

## Rule Layout

The implementation is split by rule type:

- `wenmode.rules.blocks` contains block rules such as headings, block quotes,
  lists, and fenced code.
- `wenmode.rules.inlines` contains inline rules such as links, images, inline
  code, emphasis, escapes, and raw HTML.
- `wenmode.rules.references` contains shared reference-definition extraction.

This keeps complex rules, such as lists, in their own modules while preserving a
single public import surface through `wenmode.rules`.

## Development

```bash
uv run --group test pytest -q
uv run ruff check .
uv run mypy
```
