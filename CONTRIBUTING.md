# Contributing

Thanks for helping improve Wenmode. Keep contributions focused and include the
tests or documentation needed to explain the behavior change.

## Development Setup

Wenmode uses `uv` for local development tasks. Run commands from the repository
root.

```bash
uv run --locked --group test pytest -q
uv run --locked --group lint ruff check .
uv run --locked --group lint mypy
```

Documentation tooling requires Python 3.11 or newer:

```bash
uv run --locked --group docs sphinx-build -b dirhtml docs docs/_build/html
```

For more detailed development commands, see `docs/development.md`.

## Pull Requests

- Keep changes small and scoped to one behavior, API, or documentation topic.
- Add or update tests for parser, renderer, plugin, and CLI behavior changes.
- Update documentation when public behavior, configuration, or security guidance
  changes.
- Add a `docs/changelog.md` entry for user-facing fixes, features, breaking
  changes, or performance work.
- Follow the existing commit message style, such as `fix: ...`,
  `docs: ...`, `refactor: ...`, or `refactor!: ...` for breaking refactors.

## Security

Do not open a public issue for security vulnerabilities. Follow the reporting
guidance in `docs/security.md`.
