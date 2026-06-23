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
| wenmode | 0.5.0 |
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
| docs | 106,912 | wenmode-core | 14.24ms | 7.84 | 1.00x |
| docs | 106,912 | wenmode-all | 17.20ms | 6.26 | 0.83x |
| docs | 106,912 | mistune | 20.74ms | 5.93 | 0.69x |
| docs | 106,912 | python-markdown | 64.04ms | 1.69 | 0.22x |
| docs | 106,912 | markdown-it-py | 32.50ms | 3.52 | 0.44x |
| docs | 106,912 | markdown2 | 112.57ms | 0.95 | 0.13x |
| docs | 106,912 | marko | 109.75ms | 0.99 | 0.13x |
| docs | 106,912 | commonmark.py | 79.13ms | 1.40 | 0.18x |
| rust-book | 1,225,464 | wenmode-core | 157.29ms | 8.03 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 174.84ms | 7.16 | 0.90x |
| rust-book | 1,225,464 | mistune | 226.90ms | 5.61 | 0.69x |
| rust-book | 1,225,464 | python-markdown | 623.67ms | 1.99 | 0.25x |
| rust-book | 1,225,464 | markdown-it-py | 353.84ms | 3.51 | 0.44x |
| rust-book | 1,225,464 | markdown2 | 4.149s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.161s | 1.06 | 0.14x |
| rust-book | 1,225,464 | commonmark.py | 9.710s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 27.33ms | 18.51 | 1.00x |
| progit | 502,090 | wenmode-all | 39.81ms | 14.88 | 0.69x |
| progit | 502,090 | mistune | 48.33ms | 11.29 | 0.57x |
| progit | 502,090 | python-markdown | 149.27ms | 3.47 | 0.18x |
| progit | 502,090 | markdown-it-py | 75.82ms | 7.40 | 0.36x |
| progit | 502,090 | markdown2 | 1.457s | 0.35 | 0.02x |
| progit | 502,090 | marko | 355.28ms | 1.45 | 0.08x |
| progit | 502,090 | commonmark.py | 354.44ms | 1.53 | 0.08x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
