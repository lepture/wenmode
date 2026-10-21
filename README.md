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

The top-level `Wenmode` class combines a parser and a renderer. By default,
`Wenmode` parses CommonMark-style Markdown and renders HTML.

Documentation: <https://wenmode.lepture.com>

Use Wenmode to:

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

Set `positions=True` to include source ranges for editor integration,
diagnostics, or AST-based tooling:

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

Pass a renderer when you need reStructuredText or AsciiDoc output:

```python
from wenmode import AsciiDocRenderer, Wenmode

wen = Wenmode(renderer=AsciiDocRenderer())

text = '# Hello'
expected = '= Hello\n'

asciidoc = wen.render(text)
assert asciidoc == expected
```

## Rules, presets, and plugins

Most applications start with a preset:

- `commonmark`, the default CommonMark-style rule set,
- `github`, for GitHub-flavored Markdown features such as tables and task
  lists,
- `streaming`, for incremental HTML output.

Rules are opt-in and composable. `Wenmode()` uses the `commonmark` preset by
default. Pass an explicit rule list to define a custom Markdown dialect.

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

parser = Parser(commonmark())
text = '# Hello'

tree = parser.parse(text)

html = HTMLRenderer().render(tree)
```

Use the `github` preset for GitHub-flavored Markdown features such as tables,
task lists, strikethrough, extended autolinks, and footnotes:

```python
from wenmode import Wenmode
from wenmode.presets import github

wen = Wenmode(github())
```

Use built-in plugins for non-standard syntax, document metadata, and rendering
behavior such as front matter, math, definition lists, abbreviations, spoilers,
ruby text, HTML smart punctuation, and extra inline formatting:

```python
from wenmode import Wenmode
from wenmode.plugins import inline_math

wen = Wenmode(plugins=[inline_math])

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

`wenmode-core` uses CommonMark-style rules plus pipe tables. It allows raw HTML
passthrough and disables URL sanitization to match the other HTML renderers. Mistune,
Python-Markdown, markdown-it-py, and markdown2 enable table support. Marko uses
its broader GFM helper. `commonmark.py` is a CommonMark-only baseline because it
does not support pipe tables.

`wenmode-all` uses the `github` preset plus Wenmode's built-in plugins,
including front matter, math, definition lists, abbreviations, spoilers, ruby
text, heading IDs, GitHub alerts, and additional inline formatting. The benchmark
corpora use few of these extra rules. This target measures rule dispatch
overhead, not equivalent syntax coverage.

All benchmark targets are created once before warmup and timed iterations, then
reused for every render call. Python-Markdown resets the same reusable
`Markdown` instance before each conversion.

Versions used in this snapshot:

| Library | Version |
| --- | ---: |
| wenmode | 1.0.0rc1 |
| mistune | 3.3.4 |
| mistletoe | 1.6.0 |
| python-markdown | 3.10.3 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.4 |
| commonmark.py | 0.9.2 |

Results from one local Python 3.12.9 run on an Apple M1 Pro (macOS arm64),
using `--case all --iterations 5 --warmup 2`. Mean times cover the five timed
iterations; MB/s uses the best time, and `vs core` compares mean times:

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 153,629 | wenmode-core | 24.73ms | 6.70 | 1.00x |
| docs | 153,629 | wenmode-all | 34.21ms | 4.75 | 0.72x |
| docs | 153,629 | mistune | 29.74ms | 5.26 | 0.83x |
| docs | 153,629 | mistletoe | 65.52ms | 2.47 | 0.38x |
| docs | 153,629 | python-markdown | 86.46ms | 1.81 | 0.29x |
| docs | 153,629 | markdown-it-py | 48.81ms | 3.40 | 0.51x |
| docs | 153,629 | markdown2 | 209.02ms | 0.75 | 0.12x |
| docs | 153,629 | marko | 179.56ms | 0.87 | 0.14x |
| docs | 153,629 | commonmark.py | 113.47ms | 1.39 | 0.22x |
| rust-book | 1,226,057 | wenmode-core | 168.57ms | 7.56 | 1.00x |
| rust-book | 1,226,057 | wenmode-all | 221.57ms | 5.64 | 0.76x |
| rust-book | 1,226,057 | mistune | 230.55ms | 5.44 | 0.73x |
| rust-book | 1,226,057 | mistletoe | 478.09ms | 2.60 | 0.35x |
| rust-book | 1,226,057 | python-markdown | 596.68ms | 2.08 | 0.28x |
| rust-book | 1,226,057 | markdown-it-py | 343.31ms | 3.62 | 0.49x |
| rust-book | 1,226,057 | markdown2 | 4.155s | 0.30 | 0.04x |
| rust-book | 1,226,057 | marko | 1.199s | 1.03 | 0.14x |
| rust-book | 1,226,057 | commonmark.py | 10.123s | 0.12 | 0.02x |
| progit | 502,090 | wenmode-core | 33.45ms | 17.16 | 1.00x |
| progit | 502,090 | wenmode-all | 40.22ms | 12.53 | 0.83x |
| progit | 502,090 | mistune | 41.95ms | 11.99 | 0.80x |
| progit | 502,090 | mistletoe | 149.99ms | 3.52 | 0.22x |
| progit | 502,090 | python-markdown | 134.98ms | 3.73 | 0.25x |
| progit | 502,090 | markdown-it-py | 72.07ms | 7.79 | 0.46x |
| progit | 502,090 | markdown2 | 1.437s | 0.35 | 0.02x |
| progit | 502,090 | marko | 340.23ms | 1.51 | 0.10x |
| progit | 502,090 | commonmark.py | 338.51ms | 1.58 | 0.10x |

In this run, `wenmode-core` has the lowest mean time in every case.
`wenmode-all` is faster than the other parsers on Rust Book and Pro Git;
Mistune is faster than `wenmode-all` on the docs corpus.

Benchmark numbers depend on hardware, Python version, corpus, and parser
configuration. See the full methodology in the
[Benchmarks](https://wenmode.lepture.com/benchmarks/) documentation.

## Streaming

Use the `streaming` preset to render HTML chunks before the complete document is
parsed and rendered:

```python
from wenmode import Wenmode
from wenmode.presets import streaming

wen = Wenmode(streaming())

text = '''
# Hello

A [link](/url).
'''

for chunk in wen.stream(text):
    send(chunk)
```

Pass the returned iterator to a streaming response in Django, Flask, FastAPI,
or another framework. The `streaming` preset keeps tables, strikethrough, direct
links, and direct images enabled. It excludes reference-style links, footnotes,
and other deferred document-wide transforms.

## Learn more

- [Usage](https://wenmode.lepture.com/usage/) for the main APIs.
- [Presets](https://wenmode.lepture.com/presets/) for choosing a rule set.
- [Security](https://wenmode.lepture.com/security/) for raw HTML and URL
  handling.
- [Plugins](https://wenmode.lepture.com/plugins/) for built-in extensions.
- [Migration guides](https://wenmode.lepture.com/migration/) for moving from
  other Python Markdown parsers.
