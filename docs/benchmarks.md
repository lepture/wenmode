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
| wenmode | 0.4.0 |
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

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
