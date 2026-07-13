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
| wenmode | 0.10.0 |
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
| docs | 130,412 | wenmode-core | 18.27ms | 7.75 | 1.00x |
| docs | 130,412 | wenmode-all | 19.56ms | 6.80 | 0.93x |
| docs | 130,412 | mistune | 24.33ms | 5.81 | 0.75x |
| docs | 130,412 | python-markdown | 73.37ms | 1.82 | 0.25x |
| docs | 130,412 | markdown-it-py | 40.38ms | 3.45 | 0.45x |
| docs | 130,412 | markdown2 | 149.67ms | 0.90 | 0.12x |
| docs | 130,412 | marko | 130.47ms | 1.01 | 0.14x |
| docs | 130,412 | commonmark.py | 82.41ms | 1.63 | 0.22x |
| rust-book | 1,226,076 | wenmode-core | 156.84ms | 8.05 | 1.00x |
| rust-book | 1,226,076 | wenmode-all | 174.02ms | 7.25 | 0.90x |
| rust-book | 1,226,076 | mistune | 222.01ms | 5.65 | 0.71x |
| rust-book | 1,226,076 | python-markdown | 587.86ms | 2.11 | 0.27x |
| rust-book | 1,226,076 | markdown-it-py | 335.62ms | 3.72 | 0.47x |
| rust-book | 1,226,076 | markdown2 | 4.153s | 0.30 | 0.04x |
| rust-book | 1,226,076 | marko | 1.134s | 1.12 | 0.14x |
| rust-book | 1,226,076 | commonmark.py | 9.405s | 0.14 | 0.02x |
| progit | 502,090 | wenmode-core | 31.78ms | 17.96 | 1.00x |
| progit | 502,090 | wenmode-all | 35.78ms | 15.54 | 0.89x |
| progit | 502,090 | mistune | 42.90ms | 11.77 | 0.74x |
| progit | 502,090 | python-markdown | 145.29ms | 3.48 | 0.22x |
| progit | 502,090 | markdown-it-py | 75.45ms | 7.36 | 0.42x |
| progit | 502,090 | markdown2 | 1.428s | 0.35 | 0.02x |
| progit | 502,090 | marko | 332.18ms | 1.56 | 0.10x |
| progit | 502,090 | commonmark.py | 334.09ms | 1.58 | 0.10x |

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
