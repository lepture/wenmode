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

If you are still deciding whether this model fits your application, read
{doc}`../introduce` before choosing a parser-specific migration guide.

Before changing code, collect a few representative Markdown documents from your
application and save the HTML or AST output you currently rely on. Use those
fixtures to compare Wenmode behavior during the migration.

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
3. Move plugin or extension syntax to Wenmode plugins or custom plugins.
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
| markdown2 | {doc}`markdown2` | markdown2 extras map to Wenmode presets, configured rules, or custom plugins. |
| Marko | {doc}`marko` | Marko and Wenmode both have ASTs, but node classes and extension APIs differ. |
| commonmark.py | {doc}`commonmark-py` | Wenmode can replace CommonMark HTML rendering while adding optional GFM rules and plugins. |

## Benchmark snapshot

The benchmark script includes every library covered by these migration guides.
The current snapshot uses all built-in benchmark cases:

```bash
uv run --locked --group benchmark python scripts/benchmark.py --case all
```

Lower mean time is better. These summary rows show Wenmode beside the fastest
non-Wenmode target from the migration guides:

| Case | Bytes | Wenmode mean | Fastest migration target | Target mean |
| --- | ---: | ---: | --- | ---: |
| docs | 99,098 | 12.91ms | mistune | 18.19ms |
| rust-book | 1,225,464 | 166.55ms | mistune | 236.23ms |
| progit | 502,090 | 27.28ms | mistune | 46.38ms |

Benchmark numbers are hardware- and corpus-dependent, so treat them as a local
comparison rather than a universal ranking. For the full result table, parser
configuration, dependency versions, and corpus descriptions, see
{ref}`benchmarks`.

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
