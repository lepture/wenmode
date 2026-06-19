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
| wenmode | 0.2.0 |
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
| docs | 82,426 | wenmode-core | 10.79ms | 7.81 | 1.00x |
| docs | 82,426 | wenmode-all | 13.63ms | 6.14 | 0.79x |
| docs | 82,426 | mistune | 15.15ms | 5.71 | 0.71x |
| docs | 82,426 | python-markdown | 52.32ms | 1.59 | 0.21x |
| docs | 82,426 | markdown-it-py | 25.50ms | 3.36 | 0.42x |
| docs | 82,426 | markdown2 | 83.38ms | 1.01 | 0.13x |
| docs | 82,426 | marko | 86.71ms | 0.98 | 0.12x |
| docs | 82,426 | commonmark.py | 54.85ms | 1.57 | 0.20x |
| rust-book | 1,225,464 | wenmode-core | 150.33ms | 8.31 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 169.24ms | 7.44 | 0.89x |
| rust-book | 1,225,464 | mistune | 196.07ms | 6.40 | 0.77x |
| rust-book | 1,225,464 | python-markdown | 636.59ms | 1.96 | 0.24x |
| rust-book | 1,225,464 | markdown-it-py | 363.28ms | 3.44 | 0.41x |
| rust-book | 1,225,464 | markdown2 | 4.159s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.193s | 1.03 | 0.13x |
| rust-book | 1,225,464 | commonmark.py | 9.992s | 0.12 | 0.02x |
| progit | 502,090 | wenmode-core | 26.36ms | 19.09 | 1.00x |
| progit | 502,090 | wenmode-all | 36.81ms | 16.47 | 0.72x |
| progit | 502,090 | mistune | 44.12ms | 11.52 | 0.60x |
| progit | 502,090 | python-markdown | 149.24ms | 3.39 | 0.18x |
| progit | 502,090 | markdown-it-py | 78.06ms | 7.23 | 0.34x |
| progit | 502,090 | markdown2 | 1.463s | 0.35 | 0.02x |
| progit | 502,090 | marko | 361.83ms | 1.41 | 0.07x |
| progit | 502,090 | commonmark.py | 340.45ms | 1.59 | 0.08x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
