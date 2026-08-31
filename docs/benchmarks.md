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
| wenmode | 0.14.0 |
| mistune | 3.3.4 |
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
| docs | 138,514 | wenmode-core | 21.05ms | 6.91 | 1.00x |
| docs | 138,514 | wenmode-all | 24.74ms | 5.81 | 0.85x |
| docs | 138,514 | mistune | 25.26ms | 5.54 | 0.83x |
| docs | 138,514 | mistletoe | 53.46ms | 2.60 | 0.39x |
| docs | 138,514 | python-markdown | 78.48ms | 1.84 | 0.27x |
| docs | 138,514 | markdown-it-py | 42.04ms | 3.44 | 0.50x |
| docs | 138,514 | markdown2 | 181.37ms | 0.78 | 0.12x |
| docs | 138,514 | marko | 173.29ms | 0.87 | 0.12x |
| docs | 138,514 | commonmark.py | 115.60ms | 1.39 | 0.18x |
| rust-book | 1,226,057 | wenmode-core | 168.42ms | 7.54 | 1.00x |
| rust-book | 1,226,057 | wenmode-all | 187.55ms | 6.72 | 0.90x |
| rust-book | 1,226,057 | mistune | 224.58ms | 5.60 | 0.75x |
| rust-book | 1,226,057 | mistletoe | 468.09ms | 2.63 | 0.36x |
| rust-book | 1,226,057 | python-markdown | 588.85ms | 2.10 | 0.29x |
| rust-book | 1,226,057 | markdown-it-py | 337.24ms | 3.71 | 0.50x |
| rust-book | 1,226,057 | markdown2 | 4.117s | 0.30 | 0.04x |
| rust-book | 1,226,057 | marko | 1.092s | 1.12 | 0.15x |
| rust-book | 1,226,057 | commonmark.py | 9.831s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 29.05ms | 17.30 | 1.00x |
| progit | 502,090 | wenmode-all | 38.04ms | 14.70 | 0.76x |
| progit | 502,090 | mistune | 46.85ms | 11.87 | 0.62x |
| progit | 502,090 | mistletoe | 147.81ms | 3.53 | 0.20x |
| progit | 502,090 | python-markdown | 139.58ms | 3.73 | 0.21x |
| progit | 502,090 | markdown-it-py | 74.58ms | 7.73 | 0.39x |
| progit | 502,090 | markdown2 | 1.452s | 0.35 | 0.02x |
| progit | 502,090 | marko | 331.42ms | 1.54 | 0.09x |
| progit | 502,090 | commonmark.py | 338.07ms | 1.61 | 0.09x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.

## Edge cases

Use the parser-only edge benchmark for deeply nested, unmatched, or unusually
long syntax:

```bash
uv run --group benchmark python scripts/benchmark_edges.py
```

Each case uses sizes appropriate to its structure. The suite includes deep and
deeply indented lists, alternating containers, nested link and image labels, long code-span runs,
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
