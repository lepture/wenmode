# Wenmode

Wenmode is a composable Markdown toolkit for Python by the same author as
[Mistune](https://mistune.lepture.com/). It is a rewrite informed by Mistune's
design, with a stronger focus on explicit rule composition, mdast-compatible AST
output, extension state, and pluggable rendering.

The top-level `Wenmode` class combines a parser and a renderer. By default it
parses CommonMark-style Markdown and renders HTML.

Documentation: <https://wenmode.lepture.com>

## Installation

```bash
pip install wenmode
```

## Quick start

```python
from wenmode import Wenmode

wenmode = Wenmode()

html = wenmode.render('# Hello\n\nThis is **wenmode**.')
assert html == '<h1>Hello</h1>\n<p>This is <strong>wenmode</strong>.</p>\n'
```

Use `parse()` when you need the mdast-compatible syntax tree:

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

Pass a different renderer when you want another output format:

```python
from wenmode import MarkdownRenderer, Wenmode

wenmode = Wenmode(renderer=MarkdownRenderer())

markdown = wenmode.render('# Hello\n')
assert markdown == '# Hello\n'
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

## Benchmark

Wenmode is designed so enabling more rules adds limited dispatch overhead. The
benchmark script compares Markdown-to-HTML throughput across several real-world
Markdown corpora:

```bash
uv run --group benchmark python scripts/benchmark.py --case all --iterations 3 --warmup 1
```

`wenmode-core` uses CommonMark-style rules plus pipe tables. The other parsers
are configured to match that feature set as closely as their APIs allow:
CommonMark-style parsing plus pipe table support.

`wenmode-all` uses the `github` preset plus Wenmode's remaining built-in rules,
including directives, math, definition lists, abbreviations, spoilers, ruby
text, and additional inline formatting. These extra rules are mostly unused by
the benchmark corpora, so `wenmode-all` measures the overhead of carrying many
additional rules rather than a syntax-equivalent comparison with the other
parsers.

Mean time from one local run:

| Library | docs | rust-book | progit | github-docs |
| --- | ---: | ---: | ---: | ---: |
| wenmode-core | 4.69ms | 146.90ms | 31.47ms | 3.764s |
| wenmode-all | 5.20ms | 164.07ms | 33.89ms | 4.095s |
| mistune | 7.46ms | 189.56ms | 42.65ms | 5.226s |
| markdown-it-py | 10.53ms | 348.96ms | 71.92ms | 6.738s |
| python-markdown | 23.68ms | 715.83ms | 143.70ms | 8.414s |

In this run, `wenmode-all` still remains faster than the other parsers on every
corpus even after loading many extra rules that the benchmark inputs mostly do
not use. It runs about 7-10% slower than `wenmode-core`.

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
