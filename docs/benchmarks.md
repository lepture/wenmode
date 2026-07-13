---
description: Benchmark Wenmode against Mistune, Python-Markdown, markdown-it-py, markdown2, Marko, and commonmark.py across documentation, book, and edge-case Markdown workloads.
---

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
| wenmode | 0.11.0 |
| mistune | 3.3.3 |
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
| docs | 135,115 | wenmode-core | 18.08ms | 7.84 | 1.00x |
| docs | 135,115 | wenmode-all | 20.70ms | 6.56 | 0.87x |
| docs | 135,115 | mistune | 25.42ms | 5.85 | 0.71x |
| docs | 135,115 | python-markdown | 76.18ms | 1.84 | 0.24x |
| docs | 135,115 | markdown-it-py | 39.21ms | 3.61 | 0.46x |
| docs | 135,115 | markdown2 | 158.86ms | 0.88 | 0.11x |
| docs | 135,115 | marko | 144.15ms | 1.00 | 0.13x |
| docs | 135,115 | commonmark.py | 90.95ms | 1.63 | 0.20x |
| rust-book | 1,226,076 | wenmode-core | 168.82ms | 7.80 | 1.00x |
| rust-book | 1,226,076 | wenmode-all | 181.23ms | 7.08 | 0.93x |
| rust-book | 1,226,076 | mistune | 222.76ms | 5.60 | 0.76x |
| rust-book | 1,226,076 | python-markdown | 588.23ms | 2.10 | 0.29x |
| rust-book | 1,226,076 | markdown-it-py | 337.53ms | 3.69 | 0.50x |
| rust-book | 1,226,076 | markdown2 | 4.129s | 0.30 | 0.04x |
| rust-book | 1,226,076 | marko | 1.107s | 1.12 | 0.15x |
| rust-book | 1,226,076 | commonmark.py | 10.046s | 0.12 | 0.02x |
| progit | 502,090 | wenmode-core | 28.90ms | 17.95 | 1.00x |
| progit | 502,090 | wenmode-all | 36.45ms | 15.32 | 0.79x |
| progit | 502,090 | mistune | 45.41ms | 11.94 | 0.64x |
| progit | 502,090 | python-markdown | 138.27ms | 3.72 | 0.21x |
| progit | 502,090 | markdown-it-py | 71.63ms | 7.73 | 0.40x |
| progit | 502,090 | markdown2 | 1.429s | 0.35 | 0.02x |
| progit | 502,090 | marko | 338.29ms | 1.52 | 0.09x |
| progit | 502,090 | commonmark.py | 339.19ms | 1.52 | 0.09x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.

## Edge cases

Use the parser-only edge benchmark for deeply nested, unmatched, or unusually
long syntax:

```bash
uv run --group benchmark python scripts/benchmark_edges.py
```

Each case uses sizes appropriate to its structure. The suite includes deep and
alternating containers, nested link and image labels, long code-span runs,
code-span runs inside link labels, invalid inline closers, list interruption
and continuation candidates, references, footnotes, nested HTML containers,
long HTML tag names, and wide tables. Select one case or custom sizes when
investigating a regression:

```bash
uv run --group benchmark python scripts/benchmark_edges.py \
  --case deep-blockquote --sizes 1000,2000,4000
```

Run one category when narrowing a parser layer:

```bash
uv run --group benchmark python scripts/benchmark_edges.py --category inline
```

Use `--source iterable` to parse generated line iterators instead of strings.
Use `--source stream` to benchmark incremental `Parser.parse_iter()` paths with
streaming-compatible cases; cases that require full-document transforms are
omitted from an all-case streaming run.

```bash
uv run --group benchmark python scripts/benchmark_edges.py \
  --category blocks --source stream --positions both
```

By default, each case runs both without and with source-position tracking. The
`pos-overhead` column is the enabled mean divided by the disabled mean for the
same case, source mode, and size. Use `--positions off` or `--positions on` to
run only one mode; in that case no position-overhead ratio is available.

The report also includes total time, nanoseconds per generated unit, growth
between adjacent sizes, and normalized growth. A normalized value near `1.0x`
indicates approximately linear scaling; it is a diagnostic signal rather than a
stable CI threshold.

These synthetic cases are intentionally separate from the cross-library
throughput results above. Parser recursion limits and extension semantics differ
across libraries, and MB/s is not a useful primary metric for deeply nested
structures.
