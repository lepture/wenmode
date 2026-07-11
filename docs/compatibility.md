(compatibility)=
# Compatibility

```{rst-class} lead
Understand Wenmode's current project status, Python support, Markdown coverage,
and stability expectations.
```

---

Wenmode is currently beta software. The parser, renderer, rule composition, and
documented extension APIs are ready for real integration work, but the project
may still refine edge-case behavior and smaller public APIs before a stable
1.0 release. See {ref}`changelog` for release history and upgrade notes.

For application users, the practical rule is: depend on documented presets,
rules, nodes, renderer options, and plugin APIs; avoid depending on private
helpers or incidental HTML formatting details not described in the docs.

## Python support

Wenmode supports Python 3.10 and newer. The test matrix and package metadata
cover CPython 3.10, 3.11, 3.12, 3.13, and 3.14, plus PyPy 3.10 and 3.11.

Documentation tooling currently requires Python 3.11 or newer because the docs
dependency group follows the supported versions of Sphinx and the selected
theme.

## Markdown coverage

The default `commonmark` preset targets CommonMark-style Markdown and includes
reference-style links and images. It does not include GitHub-flavored Markdown
extensions.

Use the `github` preset for GitHub-flavored Markdown features. Wenmode runs the
CommonMark and GFM spec fixture suites in its tests. Non-standard syntax is
intentionally exposed through explicit `wenmode.plugins` modules.

Use the `streaming` preset when you need incremental HTML output. Streaming
disables syntax that requires document-wide deferred inline resolution, such as
reference-style links, reference-style images, and footnotes.

## Stability expectations

The high-level APIs documented in {ref}`usage`, {ref}`presets`, {ref}`plugins`,
and {ref}`custom-plugins` are intended to be stable through the beta period:

- `Wenmode`, `Parser`, and renderer construction, including
  `Wenmode(..., plugins=[...])`.
- Rule classes and configured rule instances.
- Plugin modules or objects with `setup(wen, /)`, whether installed during
  `Wenmode` construction or later with `Wenmode.use(plugin)`.
- `Node.to_ast()` output for documented node types.
- Custom plugin `setup()` functions, rules, renderer handlers, and root
  transform shapes.
- `Parser.parse_blocks()`, `Parser.parse_inlines()`,
  `Parser.is_paragraph_interrupt()`, and `Parser.inline_source()` for custom
  rules that need nested parsing or paragraph-interruption checks.
- `BlockState`, `StateKey`, `StateStore`, `SourceMap`, and source trackers from
  `wenmode.state` for custom rules that need per-parse extension state or
  source-position mapping.
- Public helper modules such as `wenmode.ast`, `wenmode.headings`, and
  `wenmode.toc`.

The project may still adjust undocumented helper functions, renderer formatting
details for non-HTML output, and edge-case parsing behavior where the current
implementation conflicts with CommonMark, GFM, or documented Wenmode semantics.

## Public and private modules

Prefer importing public extension APIs from these modules:

- `wenmode` for `Wenmode`, `Parser`, and built-in renderers.
- `wenmode.rules` for rule base classes and built-in rule classes.
- `wenmode.plugins` for built-in plugin modules, `PluginModule`, and
  `RendererHandlers`.
- `wenmode.renderers` for renderer base classes, built-in renderers, contexts,
  and renderer handler hooks.
- `wenmode.nodes` for documented node dataclasses.
- `wenmode.state` for `BlockState`, `StateKey`, `SourceMap`, and related source
  tracking helpers used by custom rules.

Modules under `wenmode._parser` are private implementation details. They hold
the compiled rule-set, block parser, inline parser, and paragraph-interruption
logic used by `Parser`, but their classes, attributes, and helper functions are
not part of the supported extension API. Custom rules should call the public
`Parser` methods listed above instead of importing from `wenmode._parser`.

## Migration notes

Wenmode is not a drop-in replacement for Mistune plugins. The common
Markdown-to-HTML path maps directly to `Wenmode().render()`, but extension
behavior should be migrated by choosing a preset, using built-in plugins, and
registering directive renderers or custom renderers as needed.

See {ref}`recipes` for common integration patterns and {ref}`custom-plugins` for
custom plugins.
