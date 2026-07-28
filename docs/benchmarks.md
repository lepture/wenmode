---
description: Benchmark Wenmode against Mistune, mistletoe, Python-Markdown, markdown-it-py, markdown2, Marko, and commonmark.py across documentation, book, and edge-case Markdown workloads.
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

The script compares Markdown-to-HTML throughput across Wenmode and common
Python Markdown parser libraries. It reports best time, mean time, throughput,
and relative speed versus `wenmode-core`.

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
| `mistletoe` | `mistletoe.markdown`, which renders HTML and supports pipe tables by default |
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
| wenmode | 0.13.1 |
| mistune | 3.3.3 |
| mistletoe | 1.6.0 |
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
| docs | 137,185 | wenmode-core | 21.90ms | 6.98 | 1.00x |
| docs | 137,185 | wenmode-all | 25.81ms | 5.47 | 0.85x |
| docs | 137,185 | mistune | 26.50ms | 5.27 | 0.83x |
| docs | 137,185 | mistletoe | 55.55ms | 2.51 | 0.39x |
| docs | 137,185 | python-markdown | 82.21ms | 1.75 | 0.27x |
| docs | 137,185 | markdown-it-py | 44.19ms | 3.28 | 0.50x |
| docs | 137,185 | markdown2 | 175.09ms | 0.79 | 0.13x |
| docs | 137,185 | marko | 152.80ms | 0.91 | 0.14x |
| docs | 137,185 | commonmark.py | 99.19ms | 1.44 | 0.22x |
| rust-book | 1,226,057 | wenmode-core | 173.13ms | 7.21 | 1.00x |
| rust-book | 1,226,057 | wenmode-all | 198.07ms | 6.34 | 0.87x |
| rust-book | 1,226,057 | mistune | 229.78ms | 5.47 | 0.75x |
| rust-book | 1,226,057 | mistletoe | 486.00ms | 2.54 | 0.36x |
| rust-book | 1,226,057 | python-markdown | 615.24ms | 2.01 | 0.28x |
| rust-book | 1,226,057 | markdown-it-py | 346.85ms | 3.58 | 0.50x |
| rust-book | 1,226,057 | markdown2 | 4.119s | 0.30 | 0.04x |
| rust-book | 1,226,057 | marko | 1.133s | 1.09 | 0.15x |
| rust-book | 1,226,057 | commonmark.py | 9.819s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 28.08ms | 17.97 | 1.00x |
| progit | 502,090 | wenmode-all | 36.76ms | 15.12 | 0.76x |
| progit | 502,090 | mistune | 45.31ms | 12.07 | 0.62x |
| progit | 502,090 | mistletoe | 152.88ms | 3.40 | 0.18x |
| progit | 502,090 | python-markdown | 147.62ms | 3.52 | 0.19x |
| progit | 502,090 | markdown-it-py | 74.66ms | 7.37 | 0.38x |
| progit | 502,090 | markdown2 | 1.462s | 0.34 | 0.02x |
| progit | 502,090 | marko | 344.93ms | 1.47 | 0.08x |
| progit | 502,090 | commonmark.py | 333.43ms | 1.58 | 0.08x |

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
