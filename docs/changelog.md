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

### Breaking Changes

- Change `from_ast()` and `node_from_ast()` to accept `nodes=[MyNode]`
  instead of `registry={MyNode.type: MyNode}`, and remove
  `registry_from_plugins()`.
- Rename `BUILTIN_NODE_REGISTRY` to `BUILTIN_NODES`, and change built-in plugin
  `nodes` exports to node class lists instead of `{type: class}` mappings.
- Split `wenmode.plugins.math` into `wenmode.plugins.inline_math` and
  `wenmode.plugins.block_math`.
- Split `wenmode.plugins.spoiler` into `wenmode.plugins.inline_spoiler` and
  `wenmode.plugins.block_spoiler`.
- Rename constructor-time plugin option containers from `PluginSpec` to
  `PluginConfig`; `plugin(target, **options)` now returns `PluginConfig`.
- Stop exporting plugin plumbing types `Plugin`, `PluginConfig`, and
  `PluginTarget` from package facades; use `plugin()` and declarative spec APIs
  instead.
- Expose declarative plugin data as `DeclarativePluginSpec`, and allow
  declarative plugins to omit `setup()` when they expose `spec`.

### Added

- Add `AsciiDocRenderer`, CLI `--format=asciidoc` support, and built-in plugin
  handlers for best-effort serialization to AsciiDoc.
- Add `wenmode.plugins.cjk_friendly` for opt-in CJK-friendly inline parsing,
  including emphasis delimiter matching and extended autolink trailing
  punctuation handling.
- Add `wenmode.plugins.smartypants` for opt-in HTML smart punctuation rendering
  of quotes, dashes, and ellipses in plain text nodes.
- Add declarative plugin specs with `wenmode.plugins.install_declarative()`,
  and convert simple delimiter plugins such as `mark`, `insert`, and
  `inline_spoiler` to use the new Python-side installer.
- Add declarative `InlineLiteral`, `BlockFenced`, and `RendererFallback` specs
  for literal spans, fenced blocks, and wrapper-free renderer output; convert
  `inline_math` and `block_math` parsing to those specs.
- Export `RenderHandler` from `wenmode.renderers` for custom renderer handler
  type annotations.
- Add `NodeSpec` and `Node.to_spec()` for deriving static node shape metadata
  from Wenmode node classes.
- Document core and plugin AST node shape contracts and expand round-trip
  coverage for `from_ast()` with plugin node classes.

## 0.8.0

Released **Jun 29, 2026**.

- Add constructor-time plugin setup options with `wenmode.plugins.plugin()`, so
  configured plugins can be passed directly to `Wenmode(..., plugins=[...])`.
- Add `wenmode.ast.registry_from_plugins()` and expose `nodes` registries on
  built-in plugins so stored AST JSON can be restored with plugin node classes.
- Add `wenmode.presets.create_preset()` for deriving custom rule lists from
  existing presets by rule name.
- Add `Parser.supports_streaming`, `Parser.streaming_blockers()`, and matching
  `Wenmode` proxies to inspect custom streaming configurations before calling
  `stream()`.

## 0.7.0

Released **Jun 27, 2026**.

- Add `wenmode.plugins.html_container`, a non-CommonMark replacement for
  `HtmlBlock` that parses standalone HTML tag pairs as `htmlContainer` nodes
  with Markdown block children while preserving raw HTML fallback behavior for
  raw-text tags, void/self-closing tags, inline HTML, and unclosed tag pairs.
- Add structured `attributes` data to `htmlContainer` nodes and document AST
  interoperability for plugin node registries and unknown node fallback.
- Fix emphasis flanking around Unicode combining marks and format characters,
  including NFD-decomposed accents and zero-width joiner cases.

## 0.6.1

Released **Jun 26, 2026**.

- Fix emphasis parsing for CommonMark's multiple-of-3 delimiter rule when a
  delimiter run has already been partially consumed. Inputs such as `*a***a*`
  now render as `<em>a</em>*<em>a</em>` instead of leaving the second emphasis
  span unparsed.
- Fix reStructuredText rendering so image directive `alt` and `title` options
  cannot emit embedded newlines, and inline math escapes backticks correctly.

## 0.6.0

Released **Jun 24, 2026**.

- Refactor parser internals into private `_parser` modules for rule-set
  compilation, block parsing, inline parsing, and paragraph-interruption
  decisions. Public parser entry points remain on `Parser`.
- Change `Parser.parse_inlines()` to require an explicit `BlockState`, and change
  `Parser.inline_source()` to receive that state when mapping nested inline
  source ranges.
- Store active inline source maps on `BlockState` instead of the reusable
  `Parser` instance so nested inline source lookup is scoped to the active parse
  state.
- Clarify public extension API boundaries for parser helpers, `BlockState`,
  `StateKey`, `SourceMap`, renderer hooks, rules, nodes, and plugins. Modules
  under `wenmode._parser` are private implementation details.
- Add regression coverage for parser rule-set rebuilds, nested source maps,
  deferred inline queues, streaming compatibility, HTML block performance, and
  nested disallowed HTML escaping.
- Add `LiteralDirective` nodes for MyST-style fenced directives whose body
  should remain literal text. The `fenced_directive` plugin now emits
  `literalDirective` for `code-block` by default, with configurable
  `literal_names`.
- Update the local `wenmode-myst` example to use `LiteralDirective` for
  `code-block` and `sourcecode` bodies instead of carrying a local custom
  directive node.
- Add configurable fence characters to `FencedDirectiveRule` and the
  `fenced_directive` plugin. The local `wenmode-myst` example now enables
  colon fences through the shared rule instead of a custom subclass.
- Move MyST `(label)=` target support in the local `wenmode-myst` example into
  the `wenmode_myst.target` plugin module so it can be passed directly to
  `Wenmode(..., plugins=[target])`.

## 0.5.0

Released **Jun 23, 2026**.

- Add `plugins` parameter to `Wenmode` so applications can install plugins
  during construction. The existing `Wenmode.use(plugin, **options)` API
  remains supported for adding plugins after an instance exists or passing
  setup options.
- Update the CLI and local integration examples to use constructor-time plugin
  setup internally.
- Add documentation entry points for the FastAPI streaming file-upload example
  and clarify which syntax the `streaming` preset supports or deliberately
  disables.

## 0.4.0

Released **Jun 22, 2026**.

- Add `wenmode.plugins.frontmatter` for top-level `---` front matter. The
  plugin stores metadata on `root.data["frontmatter"]`, supports custom
  `load` and `dump` callbacks, preserves source positions, keeps HTML output
  metadata-free by default, serializes metadata back to Markdown, and renders
  flat metadata as RST docinfo fields.
- Add renderer root hook pseudo handlers: `root:pre` and `root:post`. Use these
  through normal renderer handler registration when a plugin needs document
  prefixes or suffixes without replacing the renderer's built-in `root`
  handler.
- Move HTML footnote sections and RST deferred image definitions to `root:post`
  hooks, keeping root rendering composable for plugins such as front matter.
- Add CLI `--plugin` support for built-in plugins on both `render` and `ast`.
- Update rule base classes to prefer class attributes such as `name`, `pattern`,
  and `trigger_chars`, while keeping configured rule instances supported.
- Add CI coverage for local examples and use locked `uv` dependency resolution
  for reproducible development and CI tasks.
- Add PyPy test coverage and publish PyPy support in package metadata.
- Update the MkDocs and Sphinx examples to use built-in plugins; Wenmode's own
  documentation now builds through the local `wenmode_myst` example instead of
  `myst_parser`.
- Expand stability and security regression coverage for renderer isolation,
  HTML attribute escaping, URL sanitization, streaming compatibility, and front
  matter rendering.

## 0.3.1

Released **Jun 21, 2026**.

- Harden `HTMLRenderer` attribute output by escaping generated attribute values,
  dropping unsafe attribute names such as event handlers and `style` by default,
  and sanitizing link and image URLs.
- Fix HTML block parsing so nested tags are preserved correctly.
- Fix normalized Markdown output for list rendering and RST output for literal
  code and links.
- Fix table parsing in custom rule lists so body lines without an unescaped pipe
  end the table instead of being padded into table rows.
- Add `Table(require_body_pipe=False)` and configure the `github` preset with it
  to preserve GFM-compatible short table body rows.
- Enforce UTF-8 output in the CLI.

## 0.3.0

Released **Jun 21, 2026**.

- Add a `wenmode` command line interface, also available with
  `python -m wenmode`, for rendering Markdown and printing AST JSON.
- Add `wenmode.ast` helpers for walking node trees, finding nodes by type or
  predicate, and extracting plain text from nodes.
- Add an introduction page and streamline the documentation index for users
  evaluating Wenmode.
- Improve stability coverage for source positions, plugin state isolation,
  streaming preset compatibility, and `parse_iter()` plugin nodes.

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
