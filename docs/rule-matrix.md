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
| `Table` | block | no | yes | no | `table`, `tableRow`, `tableCell` | none |
| `Footnote` | inline + transform | no | yes | no | `footnoteReference`, `footnoteDefinition` | none |
| `Strikethrough` | inline | no | yes | no | `delete` | none |
| `ExtendedAutolink` | inline | no | yes | no | `link` | none |

`github` configures `HtmlBlock` and `RawHtml` with the GFM disallowed tag list,
uses `RawHtml(comment_style="gfm")`, and configures `List(task=True)` so task
list markers become `listItem.checked` values. `streaming` configures
`Image(references=False)` and `Link(references=False)` to avoid document-wide
reference resolution.

## Extension-only rules

These rules are not part of the built-in `commonmark`, `github`, or `streaming`
presets. Enable them explicitly when your dialect needs the syntax.

| Rule | Kind | Generated node or behavior | Streaming note |
| --- | --- | --- | --- |
| `ReferenceDefinition` | block | stores reference definitions for `Link` and `Image` | required by reference transforms |
| `FootnoteDefinition` | block | `footnoteDefinition` | required by `Footnote` |
| `Abbreviation` | transform | rewrites matching text to `abbreviation` | not streaming-compatible |
| `DefinitionList` | continuation | `definitionList`, `definitionTerm`, `definitionDescription` | compatible |
| `MathBlock` | block | `math` | compatible |
| `BlockSpoiler` | block | `blockSpoiler` | compatible |
| `LeafDirective` | block | `leafDirective` | compatible |
| `ContainerDirective` | block | `containerDirective` | compatible |
| `FencedDirective` | block | `containerDirective` | compatible |
| `TextDirective` | inline | `textDirective` | compatible |
| `Role` | inline | `textDirective` | compatible |
| `Mark` | inline | `mark` | compatible |
| `Insert` | inline | `insert` | compatible |
| `Superscript` | inline | `superscript` | compatible |
| `Subscript` | inline | `subscript` | compatible |
| `Ruby` | inline | `ruby` | compatible |
| `InlineSpoiler` | inline | `inlineSpoiler` | compatible |
| `InlineMath` | inline | `inlineMath` | compatible |

## Streaming compatibility

Streaming works only when enabled rules do not need deferred document-wide inline
resolution. Avoid these when using `Wenmode(streaming).stream(...)`:

- `Link(references=True)` and `Image(references=True)`, because they attach
  `ReferenceTransform`.
- `Footnote`, because footnote references need collected definitions.
- `Abbreviation`, because matching text nodes are rewritten after abbreviation
  definitions are collected.

Use the `streaming` preset when latency matters. It keeps direct links and
images, but leaves shortcut and reference-style links as text.

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
from wenmode import Parser
from wenmode.rules import Image, Link

parser = Parser([
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
