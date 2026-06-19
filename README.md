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
| wenmode | 0.1.0 |
| mistune | 3.2.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

Mean time from one local `--case all` run:

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 53,792 | wenmode-core | 4.84ms | 11.58 | 1.00x |
| docs | 53,792 | wenmode-all | 5.89ms | 9.59 | 0.82x |
| docs | 53,792 | mistune | 8.64ms | 6.89 | 0.56x |
| docs | 53,792 | markdown-it-py | 13.27ms | 4.19 | 0.36x |
| docs | 53,792 | commonmark.py | 20.72ms | 2.67 | 0.23x |
| docs | 53,792 | python-markdown | 28.98ms | 1.88 | 0.17x |
| docs | 53,792 | markdown2 | 43.34ms | 1.25 | 0.11x |
| docs | 53,792 | marko | 49.65ms | 1.11 | 0.10x |
| rust-book | 1,225,464 | wenmode-core | 138.87ms | 9.07 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 156.48ms | 8.09 | 0.89x |
| rust-book | 1,225,464 | mistune | 214.92ms | 6.53 | 0.65x |
| rust-book | 1,225,464 | markdown-it-py | 360.20ms | 3.49 | 0.39x |
| rust-book | 1,225,464 | python-markdown | 624.73ms | 2.00 | 0.22x |
| rust-book | 1,225,464 | marko | 1.178s | 1.04 | 0.12x |
| rust-book | 1,225,464 | markdown2 | 4.082s | 0.30 | 0.03x |
| rust-book | 1,225,464 | commonmark.py | 9.619s | 0.14 | 0.01x |
| progit | 502,090 | wenmode-core | 26.61ms | 19.24 | 1.00x |
| progit | 502,090 | wenmode-all | 35.31ms | 16.36 | 0.75x |
| progit | 502,090 | mistune | 44.01ms | 12.40 | 0.60x |
| progit | 502,090 | markdown-it-py | 76.29ms | 7.15 | 0.35x |
| progit | 502,090 | python-markdown | 149.01ms | 3.47 | 0.18x |
| progit | 502,090 | commonmark.py | 347.45ms | 1.49 | 0.08x |
| progit | 502,090 | marko | 357.08ms | 1.43 | 0.07x |
| progit | 502,090 | markdown2 | 1.425s | 0.35 | 0.02x |

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
