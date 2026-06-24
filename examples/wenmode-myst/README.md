# wenmode-myst

`wenmode-myst` is a local example package that lets Sphinx build Markdown files
with Wenmode instead of `myst_parser`.

This is intentionally a bridge implementation:

1. Wenmode parses Markdown and MyST-like syntax into Wenmode nodes.
2. `RSTRenderer` renders those nodes to reStructuredText.
3. Sphinx parses the generated reStructuredText with its normal parser.

The package supports the syntax used by Wenmode's own documentation, including
fenced directives, colon-fenced directives, inline roles, `(label)=` targets,
tables, footnotes, and top-level scalar front matter as Sphinx metadata. It is
not a drop-in replacement for every MyST Parser feature.

Literal-body directives such as `code-block` and `sourcecode` are parsed as
Wenmode `literalDirective` nodes, so their body is passed through to
reStructuredText without Markdown inline parsing.
Colon fences are handled by the same configurable `FencedDirectiveRule` used for
backtick and tilde fences.
MyST-style `(label)=` targets live in `wenmode_myst.target`, which is a normal
Wenmode plugin module and can be passed to `Wenmode(..., plugins=[target])`.

Use it from a Sphinx `conf.py` by adding `examples/wenmode-myst/src` to
`sys.path` and replacing `myst_parser` with `wenmode_myst`.
