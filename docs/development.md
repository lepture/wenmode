(development)=
# Development

```{rst-class} lead
Run Wenmode's local test, lint, type-check, benchmark, and documentation build
tasks.
```

---

Wenmode uses `uv` for local development tasks.

Install dependencies on demand by running the task-specific `uv run --group ...`
commands below from the repository root.

Run the test suite:

```bash
uv run --group test pytest -q
```

Run linting and type checks:

```bash
uv run --group lint ruff check .
uv run --group lint mypy
```

Build the documentation:

Documentation tooling currently requires Python 3.11+.

```bash
uv run --group docs sphinx-build -b html docs docs/_build/html
```

Build with warnings treated as errors when preparing documentation changes:

```bash
uv run --group docs sphinx-build -b html docs /tmp/wenmode-docs-html -W --keep-going
```

Check external documentation links:

```bash
uv run --group docs sphinx-build -b linkcheck docs /tmp/wenmode-docs-linkcheck
```

## Documentation workflow

When changing documented behavior, update the smallest set of docs that matches
the user-facing surface:

- `usage.md` for high-level API behavior.
- `presets.md` for ready-made rule sets.
- `security.md` for renderer escaping, URL handling, and raw HTML behavior.
- `recipes.md` for copyable integration patterns.
- `migration/*.md` for parser-to-Wenmode migration guides.
- `rules.md` and `custom-rules.md` for parser extension behavior.
- `references/*.md` for rule syntax, AST shape, and default HTML output.
- `api/*.rst` for generated Python API organization.

Runnable Python examples in guide pages are exercised by
`tests/test_docs_examples.py`. Keep examples self-contained when possible. If a
snippet is intentionally partial, make sure the test skip rules identify it
explicitly rather than silently ignoring a whole page.

## Rule change checklist

When adding or changing a public rule:

- Add parser and renderer tests for recognized syntax and fallback behavior.
- Update the relevant preset documentation if the rule is enabled there.
- Update the reference page with syntax, AST shape, and HTML output.
- Add or update a recipe when the rule supports a common integration task.
- Run the strict docs build and docs example tests before release.
