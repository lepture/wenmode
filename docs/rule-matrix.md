(rule-matrix)=
# Rule matrix

```{rst-class} lead
Compare Wenmode rules by preset membership, generated nodes, configuration
options, and streaming compatibility.
```

---

Use this page when you are building a custom dialect and need to decide which
rules to enable. For syntax examples and default HTML output, use the
{ref}`reference` pages. For constructor details, use the generated
{ref}`api-rules` API page.

## Preset membership

| Rule | Kind | commonmark | github | streaming | Generated node or behavior | Options |
| --- | --- | --- | --- | --- | --- | --- |
| `ThematicBreak` | block | yes | yes | yes | `thematicBreak` | none |
| `FencedCode` | block | yes | yes | yes | `code` | none |
| `IndentedCode` | block | yes | yes | yes | `code` | none |
| `HtmlBlock` | block | yes | configured | yes | `html` | `disallowed_tags=()` |
| `List` | block | yes | configured | yes | `list`, `listItem` | `task=False` |
| `AtxHeading` | block | yes | yes | yes | `heading` | `id_transform=False` |
| `SetextHeading` | continuation | yes | yes | yes | `heading` | `id_transform=False` |
| `Blockquote` | block | yes | yes | yes | `blockquote` | none |
| `HardBreak` | inline | yes | yes | yes | `break` | none |
| `Autolink` | inline | yes | yes | yes | `link` | none |
| `RawHtml` | inline | yes | configured | yes | `html` | `disallowed_tags=()`, `comment_style="commonmark"` |
| `BackslashEscape` | inline | yes | yes | yes | text escaping | none |
| `CharacterReference` | inline | yes | yes | yes | decoded text | none |
| `Image` | inline | yes | yes | configured | `image` | `references=True` |
| `Link` | inline | yes | yes | configured | `link` | `references=True` |
| `InlineCode` | inline | yes | yes | yes | `inlineCode` | none |
| `Emphasis` | inline | yes | yes | yes | `emphasis`, `strong` | none |
| `Table` | block | no | configured | no | `table`, `tableRow`, `tableCell` | `require_body_pipe=True` |
| `Footnote` | inline + transform | no | yes | no | `footnoteReference`, `footnoteDefinition` | none |
| `Strikethrough` | inline | no | yes | no | `delete` | none |
| `ExtendedAutolink` | inline | no | yes | no | `link` | none |
| `LeafDirective` | block | no | no | no | `leafDirective` | none |
| `ContainerDirective` | block | no | no | no | `containerDirective` | none |
| `TextDirective` | inline | no | no | no | `textDirective` | none |

`github` configures `Table(require_body_pipe=False)`, configures `HtmlBlock`
and `RawHtml` with the GFM disallowed tag list, uses
`RawHtml(comment_style="gfm")`, and configures `List(task=True)` so task list
markers become `listItem.checked` values. `streaming` configures
`Image(references=False)` and `Link(references=False)` to avoid document-wide
reference resolution.

`ReferenceDefinition` is enabled automatically by `Link(references=True)` and
`Image(references=True)`. `FootnoteDefinition` is enabled automatically by
`Footnote`. You normally configure the user-facing inline rules rather than
adding those definition rules directly.

## Plugin rules

These rules are not part of `wenmode.rules`. Enable them with `Wenmode.use()`
from `wenmode.plugins` when your dialect needs the syntax.

The plugin name in the first column is the module you import from
`wenmode.plugins`.

| Plugin | Rule class | Kind | Generated node or behavior | Streaming note |
| --- | --- | --- | --- | --- |
| `abbr` | `AbbreviationRule` | transform | rewrites matching text to `abbreviation` | not streaming-compatible |
| `definition_list` | `DefinitionListRule` | continuation | `definitionList`, `definitionTerm`, `definitionDescription` | compatible |
| `frontmatter` | `FrontmatterRule` | block + transform | stores parsed data on `root.data["frontmatter"]` | compatible |
| `math` | `MathBlockRule` | block | `math` | compatible |
| `math` | `InlineMathRule` | inline | `inlineMath` | compatible |
| `spoiler` | `BlockSpoilerRule` | block | `blockSpoiler` | compatible |
| `spoiler` | `InlineSpoilerRule` | inline | `inlineSpoiler` | compatible |
| `fenced_directive` | `FencedDirectiveRule` | block | `containerDirective` | compatible |
| `inline_role` | `RoleRule` | inline | `textDirective` | compatible |
| `mark` | `MarkRule` | inline | `mark` | compatible |
| `insert` | `InsertRule` | inline | `insert` | compatible |
| `superscript` | `SuperscriptRule` | inline | `superscript` | compatible |
| `subscript` | `SubscriptRule` | inline | `subscript` | compatible |
| `ruby` | `RubyRule` | inline | `ruby` | compatible |

## Streaming compatibility

Streaming works only when enabled rules do not need deferred document-wide inline
resolution. Avoid these when using `Wenmode(streaming).stream(...)`:

- `Link(references=True)` and `Image(references=True)`, because they attach
  `ReferenceTransform`.
- `Footnote`, because footnote references need collected definitions.
- `wenmode.plugins.abbr`, because matching text nodes are rewritten after abbreviation
  definitions are collected.

Use the `streaming` preset when latency matters. It keeps direct links and
images, but leaves shortcut and reference-style links as text.

If a custom rule set raises `StreamingUnsupportedError`, compare it with this
section first. The issue is usually a rule or transform that waits for the full
document before resolving inline content.

## Common customizations

Generate heading IDs while keeping a small dialect:

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading, SetextHeading

wenmode = Wenmode([
    AtxHeading(id_transform=True),
    SetextHeading(id_transform=True),
])
```

Disable reference-style links for streaming-like behavior without using the full
streaming preset:

```python
from wenmode import Wenmode
from wenmode.rules import Image, Link

wenmode = Wenmode([
    Link(references=False),
    Image(references=False),
])
```

Filter GFM-disallowed raw HTML tags in a custom rule list:

```python
from wenmode.presets import GFM_DISALLOWED_HTML_TAGS
from wenmode.rules import HtmlBlock, RawHtml

rules = [
    HtmlBlock(disallowed_tags=GFM_DISALLOWED_HTML_TAGS),
    RawHtml(disallowed_tags=GFM_DISALLOWED_HTML_TAGS, comment_style='gfm'),
]
```
