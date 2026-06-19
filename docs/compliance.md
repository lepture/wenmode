(compliance)=
# Compliance

```{rst-class} lead
Track Wenmode's CommonMark and GitHub-flavored Markdown fixture coverage, known
differences, and compatibility expectations.
```

---

Wenmode's presets are tested against vendored CommonMark and GFM fixture files.
The tests render with `HTMLRenderer(escape=False, sanitize_urls=False)` so the
comparison focuses on parser and renderer compatibility rather than Wenmode's
safer default HTML policy.

## Fixture coverage

| Suite | Fixture | Examples | Test command | Current status |
| --- | --- | ---: | --- | --- |
| CommonMark | `commonmark-0.31.2.json` | 652 | `uv run --group test pytest -q tests/test_commonmark_spec.py` | no skipped examples |
| GFM | `gfm-0.29.json` | 677 | `uv run --group test pytest -q tests/test_gfm_spec.py` | no skipped examples |

The fixture suites exercise the `commonmark` and `github` presets. See
{ref}`presets` for feature membership; this page focuses on how those presets
are compared against upstream examples.

## GFM fixture alignment

The `github` preset includes Wenmode's `ExtendedAutolink` rule so application
users get bare URL and email autolinks by default. The GFM 0.29 fixture suite
has a separate core Autolinks section, so `tests/test_gfm_spec.py` disables
`ExtendedAutolink` for that section only. This keeps the fixture comparison
focused on the grammar under test while leaving the public `github` preset
feature-complete.

Treat future fixture failures as compatibility work items rather than stable
extensions. If your application depends on a spec edge case, keep a parser
regression test in your own integration before upgrading Wenmode.

## Compatibility boundaries

Wenmode intentionally exposes syntax through explicit rules instead of global
plugins. That means a document may render differently depending on whether you
choose `commonmark`, `github`, `streaming`, or a custom rule list.

Security defaults are also intentionally different from spec fixture rendering:

- The default HTML renderer escapes raw HTML nodes.
- `HTMLRenderer()` sanitizes unsafe link and image URLs by default.
- Fixture tests disable those options to compare against CommonMark and GFM HTML
  examples.

See {ref}`security` for production settings, and {ref}`rule-matrix` for rule
selection details.
