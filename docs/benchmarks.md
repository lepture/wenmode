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

## Edge cases

Use the parser-only edge benchmark for deeply nested, unmatched, or unusually
long syntax:

```bash
uv run --group benchmark python scripts/benchmark_edges.py
```

Each case uses sizes appropriate to its structure. The suite includes deep and
alternating containers, nested link and image labels, long code-span runs,
invalid inline closers, list interruption and continuation candidates,
references, footnotes, nested HTML containers, and wide tables. Select one case
or custom sizes when investigating a regression:

```bash
uv run --group benchmark python scripts/benchmark_edges.py \
  --case deep-blockquote --sizes 1000,2000,4000
```

Run one category when narrowing a parser layer:

```bash
uv run --group benchmark python scripts/benchmark_edges.py --category inline
```

Pass `--positions` to include source-position tracking. The report includes
total time, nanoseconds per generated unit, growth between adjacent sizes, and
normalized growth. A normalized value near `1.0x` indicates approximately
linear scaling; it is a diagnostic signal rather than a stable CI threshold.

These synthetic cases are intentionally separate from the cross-library
throughput results below. Parser recursion limits and extension semantics differ
across libraries, and MB/s is not a useful primary metric for deeply nested
structures.

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
| wenmode | 0.9.0 |
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
| docs | 122,706 | wenmode-core | 17.98ms | 7.16 | 1.00x |
| docs | 122,706 | wenmode-all | 19.56ms | 6.40 | 0.92x |
| docs | 122,706 | mistune | 22.77ms | 5.62 | 0.79x |
| docs | 122,706 | python-markdown | 72.11ms | 1.75 | 0.25x |
| docs | 122,706 | markdown-it-py | 36.95ms | 3.54 | 0.49x |
| docs | 122,706 | markdown2 | 136.93ms | 0.91 | 0.13x |
| docs | 122,706 | marko | 127.26ms | 0.97 | 0.14x |
| docs | 122,706 | commonmark.py | 73.37ms | 1.69 | 0.25x |
| rust-book | 1,225,464 | wenmode-core | 159.53ms | 8.00 | 1.00x |
| rust-book | 1,225,464 | wenmode-all | 179.00ms | 7.00 | 0.89x |
| rust-book | 1,225,464 | mistune | 217.26ms | 5.77 | 0.73x |
| rust-book | 1,225,464 | python-markdown | 612.85ms | 2.04 | 0.26x |
| rust-book | 1,225,464 | markdown-it-py | 363.94ms | 3.55 | 0.44x |
| rust-book | 1,225,464 | markdown2 | 4.168s | 0.30 | 0.04x |
| rust-book | 1,225,464 | marko | 1.139s | 1.09 | 0.14x |
| rust-book | 1,225,464 | commonmark.py | 9.583s | 0.13 | 0.02x |
| progit | 502,090 | wenmode-core | 27.32ms | 18.42 | 1.00x |
| progit | 502,090 | wenmode-all | 37.25ms | 15.73 | 0.73x |
| progit | 502,090 | mistune | 46.67ms | 11.86 | 0.59x |
| progit | 502,090 | python-markdown | 146.61ms | 3.51 | 0.19x |
| progit | 502,090 | markdown-it-py | 79.62ms | 7.21 | 0.34x |
| progit | 502,090 | markdown2 | 1.497s | 0.34 | 0.02x |
| progit | 502,090 | marko | 350.33ms | 1.45 | 0.08x |
| progit | 502,090 | commonmark.py | 327.49ms | 1.59 | 0.08x |

Benchmark numbers are hardware- and corpus-dependent. Use the command above in
your own environment before making performance-sensitive migration decisions.
