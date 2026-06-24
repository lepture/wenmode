(benchmarks)=
# Benchmarks

```{rst-class} lead
Understand Wenmode's benchmark cases, parser configuration, dependency
versions, and current Markdown-to-HTML results.
```

---

Run the benchmark suite from the repository root:

```bash
uv run --locked --group benchmark python scripts/benchmark.py --case all
```

The script compares Markdown-to-HTML throughput across Wenmode and the parser
libraries covered by the migration guides. It reports best time, mean time,
throughput, and relative speed versus `wenmode-core`.

## Cases

| Case | Source | What it represents |
| --- | --- | --- |
| `docs` | Wenmode's own `docs/*.md` files | short project documentation pages |
| `rust-book` | Rust Book Markdown files from the upstream archive | large CommonMark-style technical documentation |
| `progit` | Pro Git English Markdown files from the upstream archive | medium-size book-style Markdown with older conventions |

Remote archives are cached under the system temporary directory in
`wenmode-benchmark`.

## Parser configuration

Each benchmark target is initialized before warmup and timed iterations, then
reused across render calls.

| Target | Configuration |
| --- | --- |
| `wenmode-core` | `Wenmode([Table, *commonmark], HTMLRenderer(escape=False, sanitize_urls=False))` |
| `wenmode-all` | `github` plus directives, front matter, math, definition lists, abbreviations, spoilers, ruby, and extra formatting rules |
| `mistune` | `mistune.create_markdown(renderer='html', plugins=['table', 'speedup'])` |
| `python-markdown` | one reusable `markdown.Markdown(extensions=['tables', 'sane_lists'])`, reset before each conversion |
| `markdown-it-py` | `MarkdownIt('commonmark', {'html': True}).enable('table')` |
| `markdown2` | one reusable `markdown2.Markdown(extras=['tables'])` |
| `marko` | `marko.ext.gfm.gfm`, a reusable GFM `Markdown` instance |
| `commonmark.py` | one reusable `commonmark.Parser()` and `commonmark.HtmlRenderer()` |

The rule sets are intentionally close, not identical. Most non-Wenmode parsers
enable table support to approximate `wenmode-core`. Marko's GFM helper is
broader than tables, and `commonmark.py` is CommonMark-only because it does not
support pipe tables. `wenmode-all` is deliberately broader than the other
targets and measures the overhead of carrying many enabled rules and plugins.

That means `wenmode-core` is the closest cross-library comparison, while
`wenmode-all` answers a different question: how much overhead remains when a
Wenmode application enables many optional features.

## Versions

| Library | Version |
| --- | ---: |
| wenmode | 0.6.0 |
| mistune | 3.3.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

## Current results

These numbers are from one local Python 3.12.9 `--case all` run. Lower mean
time is better. `vs core` is relative to `wenmode-core`.

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

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
