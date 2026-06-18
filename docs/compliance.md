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
| GFM | `gfm-0.29.json` | 677 | `uv run --group test pytest -q tests/test_gfm_spec.py` | 15 documented skips |

The default `commonmark` preset targets CommonMark-style behavior plus
reference-style links and images. The `github` preset adds tables, task list
items, strikethrough, extended autolinks, footnotes, and GFM disallowed HTML tag
handling.

## Known GFM differences

The skipped GFM examples are intentionally recorded in `tests/test_gfm_spec.py`
with reasons. They currently fall into these groups:

| Area | Examples | Reason |
| --- | --- | --- |
| Tagfilter timing | 140, 141, 142, 145, 147 | configured tagfilter applies to earlier HTML block examples |
| Extended autolinks | 611, 617, 620, 621, 627, 632, 633, 635 | boundary handling differs for invalid angle links, entities, and some email/XMPP cases |
| HTML comments | 649, 650 | invalid HTML comment detection is incomplete |

Treat those differences as compatibility work items rather than stable
extensions. If your application depends on one of those edge cases, keep a
parser regression test in your own integration before upgrading Wenmode.

## Compatibility boundaries

Wenmode intentionally exposes syntax through explicit rules instead of global
plugins. That means a document may render differently depending on whether you
choose `commonmark`, `github`, `streaming`, or a custom rule list.

Security defaults are also intentionally different from spec fixture rendering:

- `HTMLRenderer()` escapes raw HTML nodes by default.
- `HTMLRenderer()` sanitizes unsafe link and image URLs by default.
- Fixture tests disable those options to compare against CommonMark and GFM HTML
  examples.

See {ref}`security` for production settings, and {ref}`rule-matrix` for rule
selection details.
