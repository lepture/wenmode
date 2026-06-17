# Development

Wenmode uses `uv` for local development tasks.

Run the test suite:

```bash
uv run --group test pytest -q
```

Run linting and type checks:

```bash
uv run ruff check .
uv run mypy
```

Build the documentation:

```bash
uv run --group docs sphinx-build -b html docs docs/_build/html
```

Build with warnings treated as errors when preparing documentation changes:

```bash
uv run --group docs sphinx-build -b html docs /tmp/wenmode-docs-html -W --keep-going
```
