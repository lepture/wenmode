(development)=
# Development

```{rst-class} lead
Run Wenmode's local test, lint, type-check, benchmark, and documentation build
tasks.
```

---

Wenmode uses `uv` for local development tasks.

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
