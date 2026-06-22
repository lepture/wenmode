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

Documentation tooling currently requires Python 3.11+.

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
- `recipes.md` for copyable integration patterns.
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
