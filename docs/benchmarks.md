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
| `wenmode-core` | `Wenmode([Table, *commonmark()], HTMLRenderer(escape=False, sanitize_urls=False))` |
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
| wenmode | 1.0.0rc1 |
| mistune | 3.3.4 |
| mistletoe | 1.6.0 |
| python-markdown | 3.10.3 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.4 |
| commonmark.py | 0.9.2 |

## Current results

These numbers are from one local Python 3.12.9 run on an Apple M1 Pro (macOS
arm64), using `--case all --iterations 5 --warmup 2`. Each target receives two
untimed warmups and five timed iterations per case. Lower mean time is better.
MB/s is input bytes divided by the best time, using decimal megabytes; `vs core`
is the `wenmode-core` mean divided by the target mean.

The docs corpus contains 153,629 bytes as captured before updating this page;
editing the documentation changes that corpus for subsequent runs.

| Case | Bytes | Library | Mean | MB/s | vs core |
| --- | ---: | --- | ---: | ---: | ---: |
| docs | 153,629 | wenmode-core | 24.73ms | 6.70 | 1.00x |
| docs | 153,629 | wenmode-all | 34.21ms | 4.75 | 0.72x |
| docs | 153,629 | mistune | 29.74ms | 5.26 | 0.83x |
| docs | 153,629 | mistletoe | 65.52ms | 2.47 | 0.38x |
| docs | 153,629 | python-markdown | 86.46ms | 1.81 | 0.29x |
| docs | 153,629 | markdown-it-py | 48.81ms | 3.40 | 0.51x |
| docs | 153,629 | markdown2 | 209.02ms | 0.75 | 0.12x |
| docs | 153,629 | marko | 179.56ms | 0.87 | 0.14x |
| docs | 153,629 | commonmark.py | 113.47ms | 1.39 | 0.22x |
| rust-book | 1,226,057 | wenmode-core | 168.57ms | 7.56 | 1.00x |
| rust-book | 1,226,057 | wenmode-all | 221.57ms | 5.64 | 0.76x |
| rust-book | 1,226,057 | mistune | 230.55ms | 5.44 | 0.73x |
| rust-book | 1,226,057 | mistletoe | 478.09ms | 2.60 | 0.35x |
| rust-book | 1,226,057 | python-markdown | 596.68ms | 2.08 | 0.28x |
| rust-book | 1,226,057 | markdown-it-py | 343.31ms | 3.62 | 0.49x |
| rust-book | 1,226,057 | markdown2 | 4.155s | 0.30 | 0.04x |
| rust-book | 1,226,057 | marko | 1.199s | 1.03 | 0.14x |
| rust-book | 1,226,057 | commonmark.py | 10.123s | 0.12 | 0.02x |
| progit | 502,090 | wenmode-core | 33.45ms | 17.16 | 1.00x |
| progit | 502,090 | wenmode-all | 40.22ms | 12.53 | 0.83x |
| progit | 502,090 | mistune | 41.95ms | 11.99 | 0.80x |
| progit | 502,090 | mistletoe | 149.99ms | 3.52 | 0.22x |
| progit | 502,090 | python-markdown | 134.98ms | 3.73 | 0.25x |
| progit | 502,090 | markdown-it-py | 72.07ms | 7.79 | 0.46x |
| progit | 502,090 | markdown2 | 1.437s | 0.35 | 0.02x |
| progit | 502,090 | marko | 340.23ms | 1.51 | 0.10x |
| progit | 502,090 | commonmark.py | 338.51ms | 1.58 | 0.10x |

`wenmode-core` has the lowest mean time in all three cases in this run.
`wenmode-all` is faster than the other parsers on Rust Book and Pro Git, while
Mistune is faster than `wenmode-all` on the docs corpus.

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.

## Edge cases

Use the parser-only edge benchmark for deeply nested, unmatched, or unusually
long syntax:

```bash
uv run --group benchmark python scripts/benchmark_edges.py
```

Each case uses sizes appropriate to its structure. The suite includes deep and
deeply indented lists, alternating containers, spoiler-like prefixes in nested
containers, nested link and image labels, long code-span runs, code-span runs
inside link labels, invalid inline closers, list interruption and continuation
candidates, references, footnotes, nested HTML containers, long HTML tag names,
and wide tables. Select one case or custom sizes when investigating a regression:

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
