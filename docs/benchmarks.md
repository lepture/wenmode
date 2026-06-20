(benchmarks)=
# Benchmarks

```{rst-class} lead
Understand Wenmode's benchmark cases, parser configuration, dependency
versions, and current Markdown-to-HTML results.
```

---

Run the benchmark suite from the repository root:

```bash
uv run --group benchmark python scripts/benchmark.py --case all
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
| `wenmode-all` | `github` plus directives, math, definition lists, abbreviations, spoilers, ruby, and extra formatting rules |
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
| wenmode | 0.2.0 |
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

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
