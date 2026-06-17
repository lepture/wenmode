# Reference

This page lists Wenmode's public rules and the nodes they produce. Each rule is
opt-in: the parser only recognizes syntax for the rules you enable.

AST examples use `root.to_ast()`. The top-level shape is always:

```python
{'type': 'root', 'children': [...]}
```

HTML examples use the default `HTMLRenderer`, which escapes raw HTML unless you
construct it with `HTMLRenderer(escape=False)`. Directive HTML can be replaced
by registering directive renderers.

## Node model

Wenmode nodes are mdast-compatible data objects. Core Markdown nodes use
mdast-style names and fields, and extensions follow the same conventions with
explicit node types.

| Node group | Node types |
| --- | --- |
| Document and containers | `root`, `paragraph`, `heading`, `blockquote`, `list`, `listItem` |
| Literals | `text`, `inlineCode`, `code`, `html`, `math`, `inlineMath` |
| Formatting | `emphasis`, `strong`, `delete`, `mark`, `insert`, `superscript`, `subscript` |
| Links and media | `link`, `image`, `break` |
| GFM and extensions | `table`, `tableRow`, `tableCell`, `footnoteReference`, `footnoteDefinition`, `abbreviation`, `definitionList`, `definitionTerm`, `definitionDescription` |
| Wenmode extensions | `ruby`, `inlineSpoiler`, `blockSpoiler` |
| Directives | `textDirective`, `leafDirective`, `containerDirective` |

## Block rules

| Rule | Syntax | Main node | AST child shape | Default HTML |
| --- | --- | --- | --- | --- |
| `AtxHeading` | `# Title` through `###### Title` | `heading` | `{'type': 'heading', 'children': [...], 'depth': 1}` | `<h1>Title</h1>` |
| `SetextHeading` | `Title` followed by `---` or `===` | `heading` | `{'type': 'heading', 'children': [...], 'depth': 2}` | `<h2>Title</h2>` |
| `ThematicBreak` | `---`, `***`, or `___` | `thematicBreak` | `{'type': 'thematicBreak'}` | `<hr />` |
| `FencedCode` | Triple backticks or tildes | `code` | `{'type': 'code', 'value': 'print(1)\n', 'lang': 'python'}` | `<pre><code class="language-python">...</code></pre>` |
| `IndentedCode` | Lines indented by four spaces or one tab | `code` | `{'type': 'code', 'value': 'print(1)\n'}` | `<pre><code>...</code></pre>` |
| `HtmlBlock` | CommonMark HTML block starts | `html` | `{'type': 'html', 'value': '<div>Hi</div>\n'}` | `&lt;div&gt;Hi&lt;/div&gt;` |
| `Blockquote` | `> quote` | `blockquote` | `{'type': 'blockquote', 'children': [...]}` | `<blockquote>...</blockquote>` |
| `List` | `- item`, `1. item`; with `task=True`, `- [x] done` | `list`, `listItem` | `{'type': 'list', 'ordered': False, 'children': [...]}` | `<ul><li>...</li></ul>` |
| `Table` | GFM pipe table | `table`, `tableRow`, `tableCell` | `{'type': 'table', 'align': ['left', 'right'], 'children': [...]}` | `<table>...</table>` |
| `Footnote` | `[^id]` and `[^id]: note` | `footnoteReference`, `footnoteDefinition` | reference nodes in paragraphs; definitions attached to root | `<sup>...</sup>` plus a footnotes section |
| `Abbreviation` | `*[HTML]: HyperText Markup Language` | `abbreviation` | `{'type': 'abbreviation', 'children': [...], 'title': '...'}` | `<abbr title="...">HTML</abbr>` |
| `DefinitionList` | `Term` followed by `: definition` | `definitionList` | `{'type': 'definitionList', 'children': [...]}` | `<dl>...</dl>` |
| `MathBlock` | `$$` fenced display math | `math` | `{'type': 'math', 'value': 'x + y\n'}` | `<div class="math math-display">...</div>` |
| `BlockSpoiler` | `>! hidden` | `blockSpoiler` | `{'type': 'blockSpoiler', 'children': [...]}` | `<div class="spoiler">...</div>` |
| `LeafDirective` | `::name[label]{attrs}` | `leafDirective` | `{'type': 'leafDirective', 'name': 'name', 'attributes': {...}, 'children': [...]}` | children fallback unless a directive renderer handles it |
| `ContainerDirective` | `:::name[label]{attrs}` body `:::` | `containerDirective` | `{'type': 'containerDirective', 'name': 'name', 'children': [...]}` | children fallback unless a directive renderer handles it |
| `FencedDirective` | ```` ```{name} label ```` with optional `:key: value` lines | `containerDirective` | same node as `ContainerDirective` | children fallback unless a directive renderer handles it |
| `BlankLine` | blank line | no node | consumes the line and returns `None` | no output |

### Structured block examples

Tables produce mdast-style table nodes:

```python
from wenmode import HTMLRenderer, Parser
from wenmode.rules import Emphasis, Table

root = Parser([Table, Emphasis]).parse(
    '| A | B |\n'
    '| :--- | ---: |\n'
    '| *x* | y |\n'
)
```

```python
{
    'type': 'root',
    'children': [{
        'type': 'table',
        'align': ['left', 'right'],
        'children': [
            {
                'type': 'tableRow',
                'children': [
                    {'type': 'tableCell', 'children': [{'type': 'text', 'value': 'A'}]},
                    {'type': 'tableCell', 'children': [{'type': 'text', 'value': 'B'}]},
                ],
            },
            {
                'type': 'tableRow',
                'children': [
                    {
                        'type': 'tableCell',
                        'children': [{'type': 'emphasis', 'children': [{'type': 'text', 'value': 'x'}]}],
                    },
                    {'type': 'tableCell', 'children': [{'type': 'text', 'value': 'y'}]},
                ],
            },
        ],
    }],
}
```

```html
<table>
<thead>
<tr>
<th align="left">A</th>
<th align="right">B</th>
</tr>
</thead>
<tbody>
<tr>
<td align="left"><em>x</em></td>
<td align="right">y</td>
</tr>
</tbody>
</table>
```

Footnotes use a document-wide transform. The reference is parsed inline, and
definitions are collected on the root.

```python
from wenmode import Parser
from wenmode.rules import Emphasis, Footnote

root = Parser([Footnote, Emphasis]).parse(
    'A note[^a].\n\n'
    '[^a]: *Footnote*.\n'
)
```

```python
{
    'type': 'root',
    'children': [
        {
            'type': 'paragraph',
            'children': [
                {'type': 'text', 'value': 'A note'},
                {'type': 'footnoteReference', 'identifier': 'a', 'label': 'a'},
                {'type': 'text', 'value': '.'},
            ],
        },
        {
            'type': 'footnoteDefinition',
            'identifier': 'a',
            'label': 'a',
            'children': [{
                'type': 'paragraph',
                'children': [
                    {'type': 'emphasis', 'children': [{'type': 'text', 'value': 'Footnote'}]},
                    {'type': 'text', 'value': '.'},
                ],
            }],
        },
    ],
}
```

The default HTML renderer emits the reference and appends a footnotes section.

```html
<p>A note<sup><a href="#user-content-fn-a" id="user-content-fnref-a" data-footnote-ref aria-describedby="footnote-label">1</a></sup>.</p>
<section data-footnotes class="footnotes">
...
</section>
```

## Inline rules

| Rule | Syntax | Main node | AST child shape | Default HTML |
| --- | --- | --- | --- | --- |
| `InlineCode` | `` `code` `` | `inlineCode` | `{'type': 'inlineCode', 'value': 'code'}` | `<code>code</code>` |
| `Emphasis` | `*em*`, `_em_`, `**strong**`, `__strong__` | `emphasis`, `strong` | `{'type': 'emphasis', 'children': [...]}` | `<em>em</em>`, `<strong>strong</strong>` |
| `Link` | `[label](/url "title")`; optionally references | `link` | `{'type': 'link', 'url': '/url', 'title': 'title', 'children': [...]}` | `<a href="/url" title="title">...</a>` |
| `Image` | `![alt](/img.png "title")`; optionally references | `image` | `{'type': 'image', 'url': '/img.png', 'alt': 'alt', 'title': 'title'}` | `<img src="/img.png" alt="alt" title="title" />` |
| `Autolink` | `<https://example.com>`, `<me@example.com>` | `link` | `{'type': 'link', 'url': 'https://example.com', 'children': [...]}` | `<a href="https://example.com">https://example.com</a>` |
| `RawHtml` | `<span>` or `</span>` inline HTML | `html` | `{'type': 'html', 'value': '<span>'}` | escaped by default |
| `BackslashEscape` | `\*` for escapable punctuation | `text` | `{'type': 'text', 'value': '*'}` | `*` |
| `CharacterReference` | `&copy;`, `&#169;`, `&amp;` | `text` | `{'type': 'text', 'value': '©'}` | `©` |
| `HardBreak` | backslash newline or two spaces before newline | `break` | `{'type': 'break'}` | `<br />` |
| `Strikethrough` | `~~delete~~` or `~delete~` | `delete` | `{'type': 'delete', 'children': [...]}` | `<del>delete</del>` |
| `ExtendedAutolink` | bare `https://example.com` or email | `link` | `{'type': 'link', 'url': 'https://example.com', 'children': [...]}` | `<a href="https://example.com">...</a>` |
| `Mark` | `==marked==` | `mark` | `{'type': 'mark', 'children': [...]}` | `<mark>marked</mark>` |
| `Insert` | `^^inserted^^` | `insert` | `{'type': 'insert', 'children': [...]}` | `<ins>inserted</ins>` |
| `Superscript` | `2^10^` | `superscript` | `{'type': 'superscript', 'children': [...]}` | `<sup>10</sup>` |
| `Subscript` | `H~2~O` | `subscript` | `{'type': 'subscript', 'children': [...]}` | `<sub>2</sub>` |
| `Ruby` | `[漢字(kanji)]` | `ruby` | `{'type': 'ruby', 'segments': [{'base': '漢字', 'text': 'kanji'}]}` | `<ruby>漢字<rt>kanji</rt></ruby>` |
| `InlineSpoiler` | `>! secret !<` | `inlineSpoiler` | `{'type': 'inlineSpoiler', 'children': [...]}` | `<span class="spoiler">secret</span>` |
| `InlineMath` | `$x + y$` | `inlineMath` | `{'type': 'inlineMath', 'value': 'x + y'}` | `<span class="math math-inline">x + y</span>` |
| `TextDirective` | `:name[label]{attrs}` | `textDirective` | `{'type': 'textDirective', 'name': 'name', 'attributes': {...}, 'children': [...]}` | children fallback unless a directive renderer handles it |
| `Role` | `` {name}`label` `` | `textDirective` | `{'type': 'textDirective', 'name': 'name', 'children': [...]}` | children fallback unless a directive renderer handles it |

### Inline examples

```python
from wenmode import Parser
from wenmode.rules import Emphasis, InlineCode, Link

root = Parser([Emphasis, Link, InlineCode]).parse(
    'A [*link*](/url) with `code`.\n'
)
```

```python
{
    'type': 'root',
    'children': [{
        'type': 'paragraph',
        'children': [
            {'type': 'text', 'value': 'A '},
            {
                'type': 'link',
                'url': '/url',
                'children': [{'type': 'emphasis', 'children': [{'type': 'text', 'value': 'link'}]}],
            },
            {'type': 'text', 'value': ' with '},
            {'type': 'inlineCode', 'value': 'code'},
            {'type': 'text', 'value': '.'},
        ],
    }],
}
```

```html
<p>A <a href="/url"><em>link</em></a> with <code>code</code>.</p>
```

## Directive rule examples

The text/leaf/container directive rules use the mdast directive node family.

```python
from wenmode import Parser
from wenmode.rules import ContainerDirective, Emphasis, LeafDirective, TextDirective

root = Parser([TextDirective, LeafDirective, ContainerDirective, Emphasis]).parse(
    ':abbr[HTML]{title="HyperText Markup Language"}\n\n'
    '::youtube[Video]{#abc}\n\n'
    ':::note[Title]{.wide}\n'
    '*Body*.\n'
    ':::\n'
)
```

```python
{
    'type': 'root',
    'children': [
        {
            'type': 'paragraph',
            'children': [{
                'type': 'textDirective',
                'name': 'abbr',
                'attributes': {'title': 'HyperText Markup Language'},
                'children': [{'type': 'text', 'value': 'HTML'}],
            }],
        },
        {
            'type': 'leafDirective',
            'name': 'youtube',
            'attributes': {'id': 'abc'},
            'children': [{'type': 'text', 'value': 'Video'}],
        },
        {
            'type': 'containerDirective',
            'name': 'note',
            'attributes': {'class': 'wide'},
            'children': [
                {
                    'type': 'paragraph',
                    'data': {'directiveLabel': True},
                    'children': [{'type': 'text', 'value': 'Title'}],
                },
                {
                    'type': 'paragraph',
                    'children': [
                        {'type': 'emphasis', 'children': [{'type': 'text', 'value': 'Body'}]},
                        {'type': 'text', 'value': '.'},
                    ],
                },
            ],
        },
    ],
}
```

Without directive renderers, HTML falls back to child content:

```html
<p>HTML</p>
Video<p>Title</p>
<p><em>Body</em>.</p>
```

`FencedDirective` and `Role` produce the same node types as container and text
directives, but use MyST-style syntax:

````markdown
```{note} Title
:class: wide

Body.
```

{abbr}`HTML`
````

The fenced directive becomes a `containerDirective` node. The role becomes a
`textDirective` node.
