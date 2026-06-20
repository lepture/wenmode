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

Use built-in plugins for non-standard syntax such as math, definition lists,
abbreviations, spoilers, ruby text, and extra inline formatting:

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

Mean time from one local Python 3.12.9 `--case all` run:

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 91,600 | wenmode-core | 12.09ms | 7.77 | 1.00x |
| docs | 91,600 | wenmode-all | 15.30ms | 6.23 | 0.79x |
| docs | 91,600 | mistune | 16.38ms | 5.74 | 0.74x |
| docs | 91,600 | python-markdown | 57.33ms | 1.65 | 0.21x |
| docs | 91,600 | markdown-it-py | 28.77ms | 3.35 | 0.42x |
| docs | 91,600 | markdown2 | 91.46ms | 1.02 | 0.13x |
| docs | 91,600 | marko | 95.04ms | 0.98 | 0.13x |
| docs | 91,600 | commonmark.py | 65.15ms | 1.50 | 0.19x |
| rust-book | 1,225,464 | wenmode-core | 156.33ms | 8.09 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 173.11ms | 7.29 | 0.90x |
| rust-book | 1,225,464 | mistune | 194.17ms | 6.44 | 0.81x |
| rust-book | 1,225,464 | python-markdown | 647.59ms | 1.93 | 0.24x |
| rust-book | 1,225,464 | markdown-it-py | 365.27ms | 3.44 | 0.43x |
| rust-book | 1,225,464 | markdown2 | 4.253s | 0.29 | 0.04x |
| rust-book | 1,225,464 | marko | 1.172s | 1.05 | 0.13x |
| rust-book | 1,225,464 | commonmark.py | 9.967s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 26.92ms | 18.89 | 1.00x |
| progit | 502,090 | wenmode-all | 37.26ms | 15.65 | 0.72x |
| progit | 502,090 | mistune | 45.42ms | 12.39 | 0.59x |
| progit | 502,090 | python-markdown | 151.11ms | 3.43 | 0.18x |
| progit | 502,090 | markdown-it-py | 77.91ms | 7.27 | 0.35x |
| progit | 502,090 | markdown2 | 1.459s | 0.35 | 0.02x |
| progit | 502,090 | marko | 352.14ms | 1.46 | 0.08x |
| progit | 502,090 | commonmark.py | 337.26ms | 1.56 | 0.08x |

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
