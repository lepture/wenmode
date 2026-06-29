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
| wenmode | 0.8.0 |
| mistune | 3.3.2 |
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
| docs | 116,875 | wenmode-core | 16.56ms | 7.54 | 1.00x |
| docs | 116,875 | wenmode-all | 18.33ms | 6.64 | 0.90x |
| docs | 116,875 | mistune | 22.28ms | 5.67 | 0.74x |
| docs | 116,875 | python-markdown | 69.72ms | 1.69 | 0.24x |
| docs | 116,875 | markdown-it-py | 34.57ms | 3.51 | 0.48x |
| docs | 116,875 | markdown2 | 129.98ms | 0.91 | 0.13x |
| docs | 116,875 | marko | 119.55ms | 1.01 | 0.14x |
| docs | 116,875 | commonmark.py | 83.65ms | 1.47 | 0.20x |
| rust-book | 1,225,464 | wenmode-core | 163.27ms | 7.66 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 197.30ms | 7.01 | 0.83x |
| rust-book | 1,225,464 | mistune | 246.29ms | 5.54 | 0.66x |
| rust-book | 1,225,464 | python-markdown | 662.25ms | 1.93 | 0.25x |
| rust-book | 1,225,464 | markdown-it-py | 358.07ms | 3.53 | 0.46x |
| rust-book | 1,225,464 | markdown2 | 4.296s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.175s | 1.07 | 0.14x |
| rust-book | 1,225,464 | commonmark.py | 10.026s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 31.54ms | 18.04 | 1.00x |
| progit | 502,090 | wenmode-all | 35.96ms | 15.51 | 0.88x |
| progit | 502,090 | mistune | 42.83ms | 11.77 | 0.74x |
| progit | 502,090 | python-markdown | 149.84ms | 3.49 | 0.21x |
| progit | 502,090 | markdown-it-py | 77.83ms | 7.28 | 0.41x |
| progit | 502,090 | markdown2 | 1.483s | 0.35 | 0.02x |
| progit | 502,090 | marko | 356.82ms | 1.45 | 0.09x |
| progit | 502,090 | commonmark.py | 346.01ms | 1.48 | 0.09x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
