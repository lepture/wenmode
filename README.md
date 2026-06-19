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

Use `parse()` when you need the mdast-compatible syntax tree:

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

Enable source positions when you need editor ranges, diagnostics, or AST-based
tooling:

```python
from wenmode import Wenmode

wenmode = Wenmode(positions=True)
ast = wenmode.parse('A **bold**.\n').to_ast()

assert ast['children'][0]['children'][1]['position'] == {
    'start': {'line': 1, 'column': 3, 'offset': 2},
    'end': {'line': 1, 'column': 11, 'offset': 10},
}
```

Pass a different renderer when you want another output format:

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

## Rules

Rules are opt-in and composable. `Wenmode()` uses the `commonmark` preset by
default; pass an explicit rule list when you want a custom Markdown dialect.

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading, FencedCode, Image, InlineCode, Link

wenmode = Wenmode([AtxHeading, FencedCode, Link, Image, InlineCode])
text = '''
# h1

hi `code` **strong**
'''
expected = '''
<h1>h1</h1>
<p>hi <code>code</code> **strong**</p>
'''

assert wenmode.render(text) == expected.lstrip()
```

Because `Emphasis` is not enabled above, `**strong**` stays as text.

Use `Parser` directly when you only need an AST and want to choose rendering
separately:

```python
from wenmode import HTMLRenderer, Parser
from wenmode.presets import commonmark

parser = Parser(commonmark)
text = '# Hello'

tree = parser.parse(text)

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
benchmark script compares Markdown-to-HTML throughput across Wenmode and the
libraries covered by the migration guides:

```bash
uv run --group benchmark python scripts/benchmark.py --case all
```

`wenmode-core` uses CommonMark-style rules plus pipe tables, with raw HTML
passthrough and URL sanitization disabled for parity with the other HTML
renderers. Mistune, Python-Markdown, markdown-it-py, and markdown2 enable table
support; Marko uses its broader GFM helper; `commonmark.py` is included as a
CommonMark-only baseline because it has no pipe table support.

`wenmode-all` uses the `github` preset plus Wenmode's built-in plugins,
including math, definition lists, abbreviations, spoilers, ruby text, and
additional inline formatting. These extra rules are mostly unused by the
benchmark corpora, so this target measures dispatch overhead rather than a
syntax-equivalent comparison.

All benchmark targets are created once before warmup and timed iterations, then
reused for every render call. Python-Markdown resets the same reusable
`Markdown` instance before each conversion.

Versions used in these snapshots:

| Library | Version |
| --- | ---: |
| wenmode | 0.2.0 |
| mistune | 3.2.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

Mean time from one local `--case all` run:

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 82,426 | wenmode-core | 10.79ms | 7.81 | 1.00x |
| docs | 82,426 | wenmode-all | 13.63ms | 6.14 | 0.79x |
| docs | 82,426 | mistune | 15.15ms | 5.71 | 0.71x |
| docs | 82,426 | python-markdown | 52.32ms | 1.59 | 0.21x |
| docs | 82,426 | markdown-it-py | 25.50ms | 3.36 | 0.42x |
| docs | 82,426 | markdown2 | 83.38ms | 1.01 | 0.13x |
| docs | 82,426 | marko | 86.71ms | 0.98 | 0.12x |
| docs | 82,426 | commonmark.py | 54.85ms | 1.57 | 0.20x |
| rust-book | 1,225,464 | wenmode-core | 150.33ms | 8.31 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 169.24ms | 7.44 | 0.89x |
| rust-book | 1,225,464 | mistune | 196.07ms | 6.40 | 0.77x |
| rust-book | 1,225,464 | python-markdown | 636.59ms | 1.96 | 0.24x |
| rust-book | 1,225,464 | markdown-it-py | 363.28ms | 3.44 | 0.41x |
| rust-book | 1,225,464 | markdown2 | 4.159s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.193s | 1.03 | 0.13x |
| rust-book | 1,225,464 | commonmark.py | 9.992s | 0.12 | 0.02x |
| progit | 502,090 | wenmode-core | 26.36ms | 19.09 | 1.00x |
| progit | 502,090 | wenmode-all | 36.81ms | 16.47 | 0.72x |
| progit | 502,090 | mistune | 44.12ms | 11.52 | 0.60x |
| progit | 502,090 | python-markdown | 149.24ms | 3.39 | 0.18x |
| progit | 502,090 | markdown-it-py | 78.06ms | 7.23 | 0.34x |
| progit | 502,090 | markdown2 | 1.463s | 0.35 | 0.02x |
| progit | 502,090 | marko | 361.83ms | 1.41 | 0.07x |
| progit | 502,090 | commonmark.py | 340.45ms | 1.59 | 0.08x |

In this run, `wenmode-all` remains faster than the other parsers even after
loading many extra rules that the benchmark inputs mostly do not use.

## Streaming

Use the `streaming` preset when you want to render HTML chunks without waiting
for the entire document to be parsed and rendered:

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wenmode = Wenmode(streaming)

text = '''
# Hello

A [link](/url).
'''

for chunk in wenmode.stream(text):
    send(chunk)
```

The returned iterator can be passed to streaming responses in frameworks such
as Django, Flask, and FastAPI.
