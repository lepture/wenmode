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

wenmode = Wenmode().use(math)

assert wenmode.render('Inline $x + y$.\n') == (
    '<p>Inline <span class="math math-inline">x + y</span>.</p>\n'
)
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
| wenmode | 0.3.0 |
| mistune | 3.2.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

Mean time from one local Python 3.12.9 `--case all` run:

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 94,647 | wenmode-core | 12.09ms | 8.10 | 1.00x |
| docs | 94,647 | wenmode-all | 15.52ms | 6.31 | 0.78x |
| docs | 94,647 | mistune | 16.52ms | 6.00 | 0.73x |
| docs | 94,647 | python-markdown | 59.05ms | 1.67 | 0.20x |
| docs | 94,647 | markdown-it-py | 29.51ms | 3.39 | 0.41x |
| docs | 94,647 | markdown2 | 121.73ms | 0.99 | 0.10x |
| docs | 94,647 | marko | 99.37ms | 0.98 | 0.12x |
| docs | 94,647 | commonmark.py | 65.06ms | 1.51 | 0.19x |
| rust-book | 1,225,464 | wenmode-core | 155.09ms | 8.21 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 170.86ms | 7.45 | 0.91x |
| rust-book | 1,225,464 | mistune | 196.98ms | 6.58 | 0.79x |
| rust-book | 1,225,464 | python-markdown | 627.38ms | 1.99 | 0.25x |
| rust-book | 1,225,464 | markdown-it-py | 373.19ms | 3.40 | 0.42x |
| rust-book | 1,225,464 | markdown2 | 4.290s | 0.29 | 0.04x |
| rust-book | 1,225,464 | marko | 1.174s | 1.06 | 0.13x |
| rust-book | 1,225,464 | commonmark.py | 9.658s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 27.27ms | 18.67 | 1.00x |
| progit | 502,090 | wenmode-all | 31.56ms | 15.95 | 0.86x |
| progit | 502,090 | mistune | 44.37ms | 12.30 | 0.61x |
| progit | 502,090 | python-markdown | 151.36ms | 3.47 | 0.18x |
| progit | 502,090 | markdown-it-py | 76.15ms | 7.31 | 0.36x |
| progit | 502,090 | markdown2 | 1.462s | 0.36 | 0.02x |
| progit | 502,090 | marko | 357.71ms | 1.44 | 0.08x |
| progit | 502,090 | commonmark.py | 339.99ms | 1.56 | 0.08x |

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
as Django, Flask, and FastAPI.

## Learn more

- [Usage](https://wenmode.lepture.com/usage/) for the main APIs.
- [Presets](https://wenmode.lepture.com/presets/) for choosing a rule set.
- [Security](https://wenmode.lepture.com/security/) for raw HTML and URL
  handling.
- [Plugins](https://wenmode.lepture.com/plugins/) for built-in extensions.
- [Migration guides](https://wenmode.lepture.com/migration/) for moving from
  other Python Markdown parsers.
