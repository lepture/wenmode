(migration)=
# Migration guides

```{rst-class} lead
Move existing Python Markdown integrations to Wenmode by mapping parser calls,
extensions, renderer behavior, AST workflows, and safety defaults.
```

---

Wenmode is not a drop-in wrapper around other Markdown parsers. It is built
around explicit rule composition and renderer dispatch, so migration is usually
best handled by identifying which syntax and output behavior your application
depends on, then choosing a preset or rule list that matches it.

```{toctree}
:maxdepth: 2

mistune
python-markdown
markdown-it-py
markdown2
marko
commonmark-py
```

## Migration strategy

Use this process for any parser migration:

1. Start with the closest preset: `commonmark`, `github`, or `streaming`.
2. Match HTML safety behavior explicitly with `HTMLRenderer` options.
3. Move plugin or extension syntax to Wenmode rules.
4. Move renderer customization to renderer handlers or directive renderers.
5. Compare rendered HTML for representative documents.
6. If your application used parser tokens or an AST, migrate that logic to
   `Node.to_ast()` or direct node traversal.

Each guide shows the existing library call first, then the equivalent Wenmode
call. Code block captions name the parser being migrated from and `wenmode`, so
you can compare the shape of the old integration with the replacement code.

## Which guide to use

| Existing parser | Start here | Most important difference |
| --- | --- | --- |
| Mistune | {doc}`mistune` | Mistune helpers enable several features by default; Wenmode makes syntax rules explicit. |
| Python-Markdown | {doc}`python-markdown` | Python-Markdown extensions often combine parsing and output behavior; Wenmode separates rules, transforms, and renderers. |
| markdown-it-py | {doc}`markdown-it-py` | markdown-it-py exposes token streams and rule chains; Wenmode exposes node objects and renderer handlers. |
| markdown2 | {doc}`markdown2` | markdown2 extras map to Wenmode presets, configured rules, or custom rules. |
| Marko | {doc}`marko` | Marko and Wenmode both have ASTs, but node classes and extension APIs differ. |
| commonmark.py | {doc}`commonmark-py` | Wenmode can replace CommonMark HTML rendering while adding optional GFM and extension rules. |

## Benchmark snapshot

The benchmark script includes every library covered by these migration guides.
The current snapshot uses all built-in benchmark cases:

```bash
uv run --group benchmark python scripts/benchmark.py --case all
```

Lower mean time is better. `vs core` is relative to `wenmode-core`, where
`1.00x` is the baseline and smaller values are slower. `commonmark.py` is
included as a CommonMark-only parser because it does not support pipe tables.

All benchmark targets are created once before warmup and timed iterations, then
reused for every render call. Python-Markdown is the exception only in that the
same `Markdown` instance is reset before each conversion, matching its reusable
API shape. Marko uses `marko.ext.gfm.gfm`, which is a reusable `Markdown`
instance rather than a newly created converter per iteration.

The rule sets are intentionally close, not identical. `wenmode-core` uses
CommonMark-style rules plus pipe tables with raw HTML passthrough and URL
sanitization disabled for parity with the other HTML renderers. Mistune,
Python-Markdown, markdown-it-py, and markdown2 enable their table support.
Marko uses its GFM helper, which is broader than just tables. `commonmark.py`
is included as a CommonMark-only baseline because it has no pipe table support.
`wenmode-all` is deliberately broader than the other targets.

Versions used in these snapshots:

| Library | Version |
| --- | ---: |
| wenmode | 0.1.0 |
| mistune | 3.2.1 |
| python-markdown | 3.10.2 |
| markdown-it-py | 4.2.0 |
| markdown2 | 2.5.5 |
| marko | 2.2.3 |
| commonmark.py | 0.9.2 |

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

Benchmark numbers are hardware- and corpus-dependent, so treat them as a local
comparison rather than a universal ranking. Run the command above in your own
environment before making performance-sensitive migration decisions.

## Common replacements

| Existing behavior | Wenmode replacement |
| --- | --- |
| Markdown string to HTML string | `Wenmode().render(text)` |
| CommonMark-style parser | `Wenmode()` or `Parser(commonmark)` |
| GitHub-flavored Markdown | `Wenmode(github)` |
| Streaming HTML chunks | `Wenmode(streaming).stream(text)` |
| Raw HTML passthrough | `Wenmode(renderer=HTMLRenderer(escape=False))` |
| Disable raw HTML syntax entirely | remove `HtmlBlock` and `RawHtml` from the rule list |
| AST as plain data | `Wenmode().parse(text).to_ast()` |
| Custom syntax | `BlockRule`, `ContinueRule`, `InlineRule`, and root transforms |
| Custom output | `BaseRenderer.register()` handlers or HTML directive renderers |

## Safety defaults

Many older Markdown integrations were configured as direct Markdown-to-HTML
filters. Wenmode's default `HTMLRenderer()` escapes raw HTML nodes and sanitizes
unsafe link and image URLs. If your previous parser allowed raw HTML through,
decide whether that was intentional before setting `HTMLRenderer(escape=False)`.

See {ref}`security` before migrating untrusted user content.
