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
| wenmode | 0.3.0 |
| mistune | 3.2.1 |
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

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
