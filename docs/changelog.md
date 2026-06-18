(changelog)=
# Changelog

```{rst-class} lead
Track user-facing changes, upgrade notes, and compatibility updates for Wenmode
releases.
```

---

This page records notable changes for released versions. Add unreleased entries
here while preparing a release, then move them under the final version heading.

## 0.1.0

Initial beta release.

- CommonMark-style parser and HTML renderer.
- GitHub-flavored Markdown preset with tables, task list items,
  strikethrough, extended autolinks, footnotes, and GFM disallowed HTML tag
  handling.
- Streaming preset for incremental HTML output.
- mdast-style AST nodes with `Node.to_ast()`.
- Pluggable renderers for HTML, normalized Markdown, and reStructuredText.
- Custom rule APIs for block, continuation, inline, and root-transform rules.
- Directive parsing and built-in HTML directive renderers.
