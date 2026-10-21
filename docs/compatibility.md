---
description: Review Wenmode project status, Python version support, Markdown coverage, public API stability, and migration expectations.
---

(compatibility)=
# Compatibility

```{rst-class} lead
Understand Wenmode's current project status, Python support, Markdown coverage,
and stability expectations.
```

---

Wenmode 1.0 is in release-candidate testing. The parser, renderer, rule composition,
and documented extension APIs form the compatibility contract for the upcoming
stable release. See {ref}`changelog` for release history and upgrade notes.

For application users, the practical rule is: depend on documented presets,
rules, nodes, renderer options, and plugin APIs; avoid depending on private
helpers or incidental HTML formatting details not described in the docs.

## Python support

Wenmode supports Python 3.11 and newer. The Linux test matrix and package
metadata cover CPython 3.11, 3.12, 3.13, and 3.14, plus PyPy 3.11.
Python 3.13 is also tested on macOS and Windows.

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

Starting with the final 1.0.0 release, Wenmode follows semantic versioning.
Backward-incompatible changes to the documented public API require a new major
version. Minor releases may add compatible APIs or syntax options; patch releases
contain compatible fixes. Release candidates may still change before the final
release, with changes recorded in the changelog.

The compatibility contract covers the APIs documented in {ref}`usage`,
{ref}`presets`, {ref}`plugins`, and {ref}`custom-plugins`, including:

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
- `BlockState`, `StateKey`, `StateStore`, `SourceCollector`, `SourceSegment`,
  `SourceMap`, and `SourceTracker` from `wenmode.state` for custom rules that
  need per-parse extension state or source-position mapping.
- Public helper modules such as `wenmode.ast`, `wenmode.headings`, and
  `wenmode.toc`.

Documented node type names, field meanings, and `Node.to_ast()` representations
are covered by this contract. New optional metadata or node types for opt-in
syntax may be added compatibly. Applications should tolerate unknown extension
nodes and optional metadata when consuming ASTs.

Fixes that align parsing with CommonMark, GFM, or documented Wenmode semantics,
and security fixes, may change output in patch releases. Such changes are
recorded in the changelog. Exact HTML whitespace and non-HTML renderer formatting
are covered only where explicitly documented. Undocumented helpers are outside
the compatibility contract.

Deprecated public APIs remain available throughout the current major version;
removals are documented for the next major release. In 1.0, pass called preset
factories, such as `Wenmode(github())`, `Parser(commonmark())`, and
`create_preset(streaming())`. Passing the factory itself is no longer supported.

## Public and private modules

Prefer importing public extension APIs from these modules:

- `wenmode` for `Wenmode`, `Parser`, and built-in renderers.
- `wenmode.rules` for rule base classes and built-in rule classes.
- `wenmode.plugins` for built-in plugin modules, `PluginModule`, and
  `RendererHandlers`.
- `wenmode.renderers` for renderer base classes, built-in renderers, contexts,
  and renderer handler hooks.
- `wenmode.nodes` for documented node dataclasses.
- `wenmode.state` for `BlockState`, `StateKey`, `SourceMap`, `SourceTracker`,
  and related source mapping helpers used by custom rules.

Modules under `wenmode._parser` are private implementation details. They hold
the compiled rule-set, block parser, inline parser, and paragraph-interruption
logic used by `Parser`, but their classes, attributes, and helper functions are
not part of the supported extension API. The `StreamBlockState` and
`StreamLineBuffer` implementation types remain importable from `wenmode.state`
for compatibility, but are outside the supported extension API. Concrete source
tracker implementations are private. Custom rules should call the public
`Parser` methods listed above instead of importing from `wenmode._parser`.

## Migration notes

Wenmode is not a drop-in replacement for Mistune plugins. The common
Markdown-to-HTML path maps directly to `Wenmode().render()`, but extension
behavior should be migrated by choosing a preset, using built-in plugins, and
registering directive renderers or custom renderers as needed.

See {ref}`recipes` for common integration patterns and {ref}`custom-plugins` for
custom plugins.
