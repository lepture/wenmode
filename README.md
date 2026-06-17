# Wenmode

Wenmode is a composable Markdown toolkit for Python by the same author as
[Mistune](https://mistune.lepture.com/). It is a rewrite informed by Mistune's
design, with a stronger focus on explicit rule composition, mdast-compatible AST
output, extension state, and pluggable rendering.

The top-level `Wenmode` class combines a parser and a renderer. By default it
parses CommonMark-style Markdown and renders HTML.

## Installation

```bash
pip install wenmode
```

## Quick start

```python
from wenmode import Wenmode

wenmode = Wenmode()

html = wenmode.render('# Hello\n\nThis is **wenmode**.')
```

Use `parse()` when you need the mdast-compatible syntax tree:

```python
from wenmode import Wenmode

wenmode = Wenmode()
tree = wenmode.parse('A [link](https://example.com).\n')
ast = tree.to_ast()
```

Pass a different renderer when you want another output format:

```python
from wenmode import MarkdownRenderer, Wenmode

wenmode = Wenmode(renderer=MarkdownRenderer())

markdown = wenmode.render('# Hello\n')
```

## Rules

Rules are opt-in and composable. `Wenmode()` uses the `commonmark` preset by
default; pass an explicit rule list when you want a custom Markdown dialect.

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading, FencedCode, Image, InlineCode, Link

wenmode = Wenmode([AtxHeading, FencedCode, Link, Image, InlineCode])

assert wenmode.render('# h1\n\nhi `code` **strong**') == (
    '<h1>h1</h1>\n<p>hi <code>code</code> **strong**</p>\n'
)
```

Because `Emphasis` is not enabled above, `**strong**` stays as text.

Use `Parser` directly when you only need an AST and want to choose rendering
separately:

```python
from wenmode import HTMLRenderer, Parser
from wenmode.presets import commonmark

parser = Parser(commonmark)
tree = parser.parse('# Hello\n')

html = HTMLRenderer().render(tree)
```

Use the `github` preset for GitHub-flavored Markdown features such as tables,
task lists, strikethrough, extended autolinks, and footnotes:

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
```

## Streaming

Use the `streaming` preset when you want to render HTML chunks without waiting
for the entire document to be parsed and rendered:

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)

for chunk in wenmode.stream('# Hello\n\nA [link](/url).\n'):
    send(chunk)
```

The returned iterator can be passed to streaming responses in frameworks such
as Django, Flask, and FastAPI.
