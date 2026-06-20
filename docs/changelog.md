(changelog)=
# Changelog

```{rst-class} lead
Track user-facing changes, upgrade notes, and compatibility updates for Wenmode
releases.
```

---

This page records notable changes for released versions. Add unreleased entries
here while preparing a release, then move them under the final version heading.

## Unreleased

## 0.2.0

Released **Jun 20, 2026**.

- Add the `Wenmode.use(plugin, **options)` plugin API and built-in
  `wenmode.plugins` modules for non-standard syntax such as math, definition
  lists, abbreviations, spoilers, ruby text, inline roles, and extra inline
  formatting.
- Add opt-in source positions with `Wenmode(..., positions=True)` and
  `Parser(..., positions=True)`. `Root.to_ast()` includes unist-style
  `position.start` and `position.end` objects when positions are enabled, while
  internal `Position` objects store offsets for cheaper parsing and simpler
  custom rule code.
- Add source mapping helpers for custom rules that recursively parse nested
  inline or block content.
- Require custom `InlineRule.parse()` implementations to receive a concrete
  `BlockState`; `Parser.parse_inlines()` remains the standalone inline parsing
  entry point.
- Move non-standard extension syntax out of `wenmode.rules` and into explicit
  plugins. Code using those extension rules directly should migrate to
  `Wenmode().use(wenmode.plugins.<name>)`.

## 0.1.1

Released **Jun 19, 2026**.

- Avoid potential regex DoS cases in ATX heading parsing, inline directives,
  spoiler spans, and extended autolink trimming.
- Change `RootTransform` from a protocol to a base class with default no-op
  hooks, making custom root transforms easier to define without requiring
  boilerplate `prepare()` methods.
- Improve `StateKey` type hints for typed parser extension state.

## 0.1.0

Released **Jun 18, 2026**.

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
