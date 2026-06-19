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

## Versions

| Library | Version |
| --- | ---: |
| wenmode | 0.1.0 |
| mistune | 3.2.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

## Current results

These numbers are from one local `--case all` run. Lower mean time is better.
`vs core` is relative to `wenmode-core`.

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 53,792 | wenmode-core | 4.84ms | 11.58 | 1.00x |
| docs | 53,792 | wenmode-all | 5.89ms | 9.59 | 0.82x |
| docs | 53,792 | mistune | 8.64ms | 6.89 | 0.56x |
| docs | 53,792 | markdown-it-py | 13.27ms | 4.19 | 0.36x |
| docs | 53,792 | commonmark.py | 20.72ms | 2.67 | 0.23x |
| docs | 53,792 | python-markdown | 28.98ms | 1.88 | 0.17x |
| docs | 53,792 | markdown2 | 43.34ms | 1.25 | 0.11x |
| docs | 53,792 | marko | 49.65ms | 1.11 | 0.10x |
| rust-book | 1,225,464 | wenmode-core | 138.87ms | 9.07 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 156.48ms | 8.09 | 0.89x |
| rust-book | 1,225,464 | mistune | 214.92ms | 6.53 | 0.65x |
| rust-book | 1,225,464 | markdown-it-py | 360.20ms | 3.49 | 0.39x |
| rust-book | 1,225,464 | python-markdown | 624.73ms | 2.00 | 0.22x |
| rust-book | 1,225,464 | marko | 1.178s | 1.04 | 0.12x |
| rust-book | 1,225,464 | markdown2 | 4.082s | 0.30 | 0.03x |
| rust-book | 1,225,464 | commonmark.py | 9.619s | 0.14 | 0.01x |
| progit | 502,090 | wenmode-core | 26.61ms | 19.24 | 1.00x |
| progit | 502,090 | wenmode-all | 35.31ms | 16.36 | 0.75x |
| progit | 502,090 | mistune | 44.01ms | 12.40 | 0.60x |
| progit | 502,090 | markdown-it-py | 76.29ms | 7.15 | 0.35x |
| progit | 502,090 | python-markdown | 149.01ms | 3.47 | 0.18x |
| progit | 502,090 | commonmark.py | 347.45ms | 1.49 | 0.08x |
| progit | 502,090 | marko | 357.08ms | 1.43 | 0.07x |
| progit | 502,090 | markdown2 | 1.425s | 0.35 | 0.02x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
