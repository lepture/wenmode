<div align="center">

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="docs/_static/dark-logo.svg" />
  <img alt="Wenmode" src="docs/_static/light-logo.svg" height="68" />
</picture>

[![Build Status](https://img.shields.io/github/actions/workflow/status/lepture/wenmode/test.yml?logo=github&label=test)](https://github.com/lepture/wenmode/actions)
[![PyPI version](https://img.shields.io/pypi/v/wenmode?logo=python&logoColor=fff&labelColor=3776ab)](https://pypi.org/project/wenmode)
[![Code Coverage](https://img.shields.io/codecov/c/github/lepture/wenmode)](https://codecov.io/gh/lepture/wenmode)
[![Maintainability Rating](https://sonarcloud.io/api/project_badges/measure?project=lepture_wenmode&metric=sqale_rating)](https://sonarcloud.io/summary/new_code?id=lepture_wenmode)
[![Security Rating](https://sonarcloud.io/api/project_badges/measure?project=lepture_wenmode&metric=security_rating)](https://sonarcloud.io/summary/new_code?id=lepture_wenmode)

</div>

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

wen = Wenmode()

text = '''
# Hello

This is **wenmode**.
'''
expected = '''
<h1>Hello</h1>
<p>This is <strong>wenmode</strong>.</p>
'''

html = wen.render(text)
assert html == expected.lstrip()
```

Use `parse()` when you need the mdast-compatible syntax tree:

```python
from wenmode import Wenmode

wen = Wenmode()
text = 'A [link](https://example.com).'

tree = wen.parse(text)
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

wen = Wenmode(positions=True)
ast = wen.parse('A **bold**.\n').to_ast()

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

wen = Wenmode(renderer=RSTRenderer())

text = '# Hello'
expected = '''
Hello
=====
'''

rst = wen.render(text)
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

wen = Wenmode([AtxHeading, FencedCode, Link, Image, InlineCode])
text = '''
# h1

hi `code` **strong**
'''
expected = '''
<h1>h1</h1>
<p>hi <code>code</code> **strong**</p>
'''

assert wen.render(text) == expected.lstrip()
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

wen = Wenmode(github)
```

Use built-in plugins for non-standard syntax and document metadata such as
front matter, math, definition lists, abbreviations, spoilers, ruby text, and
extra inline formatting:

```python
from wenmode import Wenmode
from wenmode.plugins import math

wen = Wenmode(plugins=[math])

assert wen.render('Inline $x + y$.\n') == (
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
| wenmode | 0.6.0 |
| mistune | 3.3.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

Mean time from one local Python 3.12.9 `--case all` run:

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 112,008 | wenmode-core | 15.14ms | 7.91 | 1.00x |
| docs | 112,008 | wenmode-all | 16.82ms | 6.78 | 0.90x |
| docs | 112,008 | mistune | 19.45ms | 6.10 | 0.78x |
| docs | 112,008 | python-markdown | 67.11ms | 1.70 | 0.23x |
| docs | 112,008 | markdown-it-py | 32.99ms | 3.64 | 0.46x |
| docs | 112,008 | markdown2 | 116.22ms | 0.97 | 0.13x |
| docs | 112,008 | marko | 113.94ms | 1.01 | 0.13x |
| docs | 112,008 | commonmark.py | 81.95ms | 1.44 | 0.18x |
| rust-book | 1,225,464 | wenmode-core | 164.63ms | 8.11 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 172.92ms | 7.37 | 0.95x |
| rust-book | 1,225,464 | mistune | 220.94ms | 5.70 | 0.75x |
| rust-book | 1,225,464 | python-markdown | 611.94ms | 2.05 | 0.27x |
| rust-book | 1,225,464 | markdown-it-py | 357.72ms | 3.59 | 0.46x |
| rust-book | 1,225,464 | markdown2 | 4.112s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.155s | 1.08 | 0.14x |
| rust-book | 1,225,464 | commonmark.py | 9.493s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 27.84ms | 18.07 | 1.00x |
| progit | 502,090 | wenmode-all | 32.23ms | 15.64 | 0.86x |
| progit | 502,090 | mistune | 45.91ms | 11.90 | 0.61x |
| progit | 502,090 | python-markdown | 152.38ms | 3.53 | 0.18x |
| progit | 502,090 | markdown-it-py | 76.49ms | 7.30 | 0.36x |
| progit | 502,090 | markdown2 | 1.466s | 0.35 | 0.02x |
| progit | 502,090 | marko | 355.99ms | 1.45 | 0.08x |
| progit | 502,090 | commonmark.py | 392.68ms | 1.46 | 0.07x |

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

wen = Wenmode(streaming)

text = '''
# Hello

A [link](/url).
'''

for chunk in wen.stream(text):
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
