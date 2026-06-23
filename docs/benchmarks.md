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
| docs | 109,547 | wenmode-core | 15.59ms | 7.48 | 1.00x |
| docs | 109,547 | wenmode-all | 17.75ms | 6.35 | 0.88x |
| docs | 109,547 | mistune | 19.69ms | 5.98 | 0.79x |
| docs | 109,547 | python-markdown | 65.10ms | 1.69 | 0.24x |
| docs | 109,547 | markdown-it-py | 32.75ms | 3.49 | 0.48x |
| docs | 109,547 | markdown2 | 115.76ms | 0.95 | 0.13x |
| docs | 109,547 | marko | 111.86ms | 0.99 | 0.14x |
| docs | 109,547 | commonmark.py | 78.77ms | 1.47 | 0.20x |
| rust-book | 1,225,464 | wenmode-core | 161.52ms | 7.80 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 179.90ms | 6.96 | 0.90x |
| rust-book | 1,225,464 | mistune | 219.93ms | 5.67 | 0.73x |
| rust-book | 1,225,464 | python-markdown | 617.35ms | 2.01 | 0.26x |
| rust-book | 1,225,464 | markdown-it-py | 348.20ms | 3.59 | 0.46x |
| rust-book | 1,225,464 | markdown2 | 4.070s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.154s | 1.06 | 0.14x |
| rust-book | 1,225,464 | commonmark.py | 9.086s | 0.14 | 0.02x |
| progit | 502,090 | wenmode-core | 27.82ms | 18.21 | 1.00x |
| progit | 502,090 | wenmode-all | 32.07ms | 15.72 | 0.87x |
| progit | 502,090 | mistune | 45.91ms | 11.93 | 0.61x |
| progit | 502,090 | python-markdown | 148.01ms | 3.47 | 0.19x |
| progit | 502,090 | markdown-it-py | 75.63ms | 7.35 | 0.37x |
| progit | 502,090 | markdown2 | 1.446s | 0.35 | 0.02x |
| progit | 502,090 | marko | 354.47ms | 1.44 | 0.08x |
| progit | 502,090 | commonmark.py | 326.07ms | 1.61 | 0.09x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
