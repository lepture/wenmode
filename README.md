# Wenmode

Wenmode is a composable Markdown toolkit for Python by the same author as
[Mistune](https://mistune.lepture.com/). It is a rewrite informed by Mistune's
design, with a stronger focus on explicit rule composition, mdast-compatible AST
output, extension state, and pluggable rendering.

The top-level `Wenmode` class combines a parser and a renderer. By default it
parses CommonMark-style Markdown and renders HTML.

Documentation: <https://wenmode.lepture.com>

Use Wenmode when you need one or more of these behaviors:

- render Markdown to HTML with safe defaults for user-authored content,
- choose the exact Markdown rules your application accepts,
- inspect or store an mdast-compatible AST,
- build a custom Markdown dialect with parser rules and renderer handlers,
- stream HTML output from Markdown input.

## Installation

```bash
pip install wenmode
```

Run the CLI without installing it permanently:

```bash
uvx wenmode render --preset=github README.md
uvx wenmode ast --preset=github README.md
```

After installation, use either the console script or Python module entry point:

```bash
wenmode render README.md --preset=github
python -m wenmode ast README.md --positions
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

assert ast['children'][0] == {
    'type': 'paragraph',
    'position': {
        'start': {'line': 1, 'column': 1, 'offset': 0},
        'end': {'line': 2, 'column': 1, 'offset': 12}
    },
    'children': [
        {
            'type': 'text',
            'position': {
                'start': {'line': 1, 'column': 1, 'offset': 0},
                'end': {'line': 1, 'column': 3, 'offset': 2}
            },
            'value': 'A '
        },
        {
            'type': 'strong',
            'position': {
                'start': {'line': 1, 'column': 3, 'offset': 2},
                'end': {'line': 1, 'column': 11, 'offset': 10}
            },
            'children': [
                {
                    'type': 'text',
                    'position': {
                        'start': {'line': 1, 'column': 5, 'offset': 4},
                        'end': {'line': 1, 'column': 9, 'offset': 8}
                    },
                    'value': 'bold'
                }
            ]
        },
        {
            'type': 'text',
            'position': {
                'start': {'line': 1, 'column': 11, 'offset': 10},
                'end': {'line': 1, 'column': 12, 'offset': 11}
            },
            'value': '.'
        }
    ]
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

## Rules, presets, and plugins

Most applications start with a preset:

- `commonmark`, the default CommonMark-style rule set,
- `github`, for GitHub-flavored Markdown features such as tables and task
  lists,
- `streaming`, for incremental HTML output.

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

Use built-in plugins for non-standard syntax and document metadata such as
front matter, math, definition lists, abbreviations, spoilers, ruby text, and
extra inline formatting:

```python
from wenmode import Wenmode
from wenmode.plugins import math

wenmode = Wenmode(plugins=[math])

assert wenmode.render('Inline $x + y$.\n') == (
    '<p>Inline <span class="math math-inline">x + y</span>.</p>\n'
)
```

## Benchmark

Wenmode is designed so enabling more rules adds limited dispatch overhead. The
benchmark script compares Markdown-to-HTML throughput across Wenmode and the
libraries covered by the migration guides:

```bash
uv run --locked --group benchmark python scripts/benchmark.py --case all
```

`wenmode-core` uses CommonMark-style rules plus pipe tables, with raw HTML
passthrough and URL sanitization disabled for parity with the other HTML
renderers. Mistune, Python-Markdown, markdown-it-py, and markdown2 enable table
support; Marko uses its broader GFM helper; `commonmark.py` is included as a
CommonMark-only baseline because it has no pipe table support.

`wenmode-all` uses the `github` preset plus Wenmode's built-in plugins,
including front matter, math, definition lists, abbreviations, spoilers, ruby
text, and additional inline formatting. These extra rules are mostly unused by the
benchmark corpora, so this target measures dispatch overhead rather than a
syntax-equivalent comparison.

All benchmark targets are created once before warmup and timed iterations, then
reused for every render call. Python-Markdown resets the same reusable
`Markdown` instance before each conversion.

Versions used in these snapshots:

| Library | Version |
| --- | ---: |
| wenmode | 0.4.0 |
| mistune | 3.3.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

Mean time from one local Python 3.12.9 `--case all` run:

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 99,098 | wenmode-core | 12.91ms | 8.16 | 1.00x |
| docs | 99,098 | wenmode-all | 16.07ms | 6.48 | 0.80x |
| docs | 99,098 | mistune | 18.19ms | 6.03 | 0.71x |
| docs | 99,098 | python-markdown | 69.56ms | 1.68 | 0.19x |
| docs | 99,098 | markdown-it-py | 29.83ms | 3.54 | 0.43x |
| docs | 99,098 | markdown2 | 118.38ms | 0.99 | 0.11x |
| docs | 99,098 | marko | 100.76ms | 1.00 | 0.13x |
| docs | 99,098 | commonmark.py | 66.90ms | 1.52 | 0.19x |
| rust-book | 1,225,464 | wenmode-core | 166.55ms | 7.98 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 204.81ms | 6.35 | 0.81x |
| rust-book | 1,225,464 | mistune | 236.23ms | 5.43 | 0.71x |
| rust-book | 1,225,464 | python-markdown | 628.04ms | 1.98 | 0.27x |
| rust-book | 1,225,464 | markdown-it-py | 354.12ms | 3.51 | 0.47x |
| rust-book | 1,225,464 | markdown2 | 4.184s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.151s | 1.08 | 0.14x |
| rust-book | 1,225,464 | commonmark.py | 9.484s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 27.28ms | 18.57 | 1.00x |
| progit | 502,090 | wenmode-all | 40.08ms | 15.88 | 0.68x |
| progit | 502,090 | mistune | 46.38ms | 11.73 | 0.59x |
| progit | 502,090 | python-markdown | 149.56ms | 3.47 | 0.18x |
| progit | 502,090 | markdown-it-py | 80.91ms | 7.16 | 0.34x |
| progit | 502,090 | markdown2 | 1.445s | 0.35 | 0.02x |
| progit | 502,090 | marko | 353.44ms | 1.44 | 0.08x |
| progit | 502,090 | commonmark.py | 345.81ms | 1.61 | 0.08x |

In this run, `wenmode-all` remains faster than the other parsers even after
loading many extra rules that the benchmark inputs mostly do not use.

Benchmark numbers depend on hardware, Python version, corpus, and parser
configuration. See the full methodology in the
[Benchmarks](https://wenmode.lepture.com/benchmarks/) documentation.

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
as Django, Flask, and FastAPI. The `streaming` preset keeps tables,
strikethrough, direct links, and direct images enabled, while reference-style
links, footnotes, and other deferred document-wide transforms stay out of the
streaming path.

## Learn more

- [Usage](https://wenmode.lepture.com/usage/) for the main APIs.
- [Presets](https://wenmode.lepture.com/presets/) for choosing a rule set.
- [Security](https://wenmode.lepture.com/security/) for raw HTML and URL
  handling.
- [Plugins](https://wenmode.lepture.com/plugins/) for built-in extensions.
- [Migration guides](https://wenmode.lepture.com/migration/) for moving from
  other Python Markdown parsers.
