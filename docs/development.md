---
description: Develop Wenmode locally with documented setup, tests, docs builds, release checks, and contribution conventions.
---

(development)=
# Development

```{rst-class} lead
Run Wenmode's local test, lint, type-check, benchmark, and documentation build
tasks.
```

---

Wenmode uses `uv` for local development tasks. The repository tracks
`uv.lock`, so release and CI checks should use `uv run --locked ...`.

Install dependencies on demand by running the task-specific commands below from
the repository root.

Run the test suite:

```bash
uv run --locked --group test pytest -q
```

Run linting and type checks:

```bash
uv run --locked --group lint ruff check .
uv run --locked --group lint mypy
```

Build the documentation:

```bash
uv run --locked --group docs sphinx-build -b dirhtml docs docs/_build/html
```

Build with warnings treated as errors when preparing documentation changes:

```bash
uv run --locked --group docs sphinx-build -b dirhtml docs /tmp/wenmode-docs-html -W --keep-going
```

Check external documentation links:

```bash
uv run --locked --group docs sphinx-build -b linkcheck docs /tmp/wenmode-docs-linkcheck
```

Run the local integration examples:

```bash
uv run --directory examples/wenmode-fastapi --locked --group test pytest -q
uv run --directory examples/wenmode-docx --locked --group test pytest -q
uv run --directory examples/wenmode-mkdocs --locked --group test pytest -q
uv run --directory examples/wenmode-myst --locked --group test pytest -q
```

## Documentation workflow

Wenmode's own documentation is built through the local `wenmode_myst` example
instead of `myst_parser`. `docs/conf.py` imports
`examples/wenmode-myst/src/wenmode_myst`, and the extension converts Markdown to
reStructuredText with Wenmode before Sphinx parses it.

When changing documented behavior, update the smallest set of docs that matches
the user-facing surface:

- `usage.md` for high-level API behavior.
- `presets.md` for ready-made rule sets.
- `security.md` for renderer escaping, URL handling, and raw HTML behavior.
- `rule-matrix.md` for rule options, preset membership, and streaming support.
- `compliance.md` for CommonMark/GFM fixture coverage and known differences.
- `changelog.md` for user-facing changes, upgrade notes, and compatibility updates.
- `benchmarks.md` for benchmark methodology, versions, and results.
- `troubleshooting.md` for common integration failures and fixes.
- `recipes/` for copyable integration patterns.
- `integrations.md` for end-to-end application pipelines.
- `migration/*.md` for parser-to-Wenmode migration guides.
- `plugins.md` and `custom-plugins.md` for plugin extension behavior.
- `references/*.md` for rule syntax, AST shape, and default HTML output.
- `api/*.rst` for generated Python API organization.

Runnable Python examples in guide pages are exercised by
`tests/test_docs_examples.py`. Keep examples self-contained when possible. If a
snippet is intentionally partial, make sure the test skip rules identify it
explicitly rather than silently ignoring a whole page.

When a change affects multiple pages, update the conceptual page first, then the
recipe or reference page that users copy from. This keeps explanations and code
examples aligned.

## Rule change checklist

When adding or changing a public rule or built-in plugin:

- Add parser and renderer tests for recognized syntax and fallback behavior.
- Update the relevant preset documentation if the rule is enabled there.
- Keep non-standard syntax in `wenmode.plugins`, with node classes and renderer
  handlers owned by the plugin module.
- Update the reference page with syntax, AST shape, and HTML output.
- Add or update a recipe when the rule supports a common integration task.
- Run the strict docs build and docs example tests before release.


## Parser grammar and resource boundaries

Validate the grammar before collecting or normalizing a candidate. Prefer a
normative bound, such as the numeric-reference digit count or reference-label
length, over a cache for syntax that can already be rejected. Do not add arbitrary
limits to valid URLs, HTML attributes, or backtick lengths. Successful scans that
consume their searched span are already bounded by input size; cache failed
suffix searches or index reusable closers when later candidates can revisit them.

All nested Markdown must use the parser's shared semantic budget. Root content
starts at depth zero. A content wrapper costs one level; root, paragraph, heading,
list item, definition term/description, and table row/cell nodes are scaffolding.
A table itself costs one level. Keep paragraph-interruption decisions outside a
container's content context. Deferred inline work must retain its origin depth.

The current nested parsing entrypoints are:

| Content | Entry boundary |
| --- | --- |
| Blockquotes, lists, alerts, footnotes | Nested block parsing |
| Container/fenced directives, HTML containers, block spoilers, definition descriptions | Nested block parsing |
| Declarative block rules with children | Nested block parsing |
| Links, image alt text, text directives, roles, strikethrough, subscript/superscript | Nested inline parsing |
| Declarative inline rules, including inline spoilers | Nested inline parsing |
| Directive labels, definition terms, table cells, shallow list/spoiler content | Explicit nested content context around inline parsing |
| Emphasis and abbreviation replacement | Shared semantic node policy and remaining budget |

Custom rules should call `Parser.parse_blocks()` and `Parser.parse_inlines()`.
A block rule parsing a container label directly uses `state.nested_content()`
around its inline call. Transforms that insert wrappers must carry semantic depth
and leave existing text unchanged when no level remains. Boundary and exception
regressions should cover mixed rule types, deferred references, positions, and
streaming; a separate per-rule quota cannot replace the shared budget.

Cache immutable source identity and the syntax options that affect a result.
Keep source caches in document state, never on reusable parser/rule instances.
Block indexes must distinguish nested states and use absolute stream indices;
discarded lines must not invalidate future pairings. Retain ordinary matched-span
fast paths. Add deterministic operation counts alongside bounded scaling tests.

Serialized AST restoration has separate structural depth/node budgets. Validate
known node type, scalar fields, and child shapes before allocating descendants;
retain cycle checks and custom-node support. Do not impose the Markdown semantic
budget on restored or trusted custom AST rendering and traversal.

The resource review also considered frontmatter and literal fences (consumed
once), definition-list and footnote scans, ruby segmentation, and parsed/restored
AST traversal helpers. They require no additional parser cap or rescan cache.
