(directives)=
# Directives

```{rst-class} lead
Use mdast-style directive syntax and directive renderers to add structured
Markdown extensions.
```

---

Wenmode's core directive rules follow the mdast directive model used by
[`mdast-util-directive`](https://github.com/syntax-tree/mdast-util-directive)
and remark directives. They create mdast-compatible `textDirective`,
`leafDirective`, and `containerDirective` nodes.

Directive parsing and directive rendering are separate steps:

1. Enable directive syntax rules so the parser creates directive nodes.
2. Register directive renderers when you want special HTML output.

Without a matching HTML directive renderer, Wenmode falls back to rendering the
directive children.

Use directives when your document needs named, structured blocks or spans such
as admonitions, figures, details sections, or a table of contents. Use plugins
when the syntax should create a new Wenmode-specific node type such as `math`,
`ruby`, or `mark`.

MyST-style fenced directives and inline roles are plugins. See {ref}`plugins`
when you want code-fence-style `` ```{name} `` directives or
`` {name}`content` `` roles. The fenced directive plugin can also emit
`literalDirective` nodes for literal-body names such as `code-block`; the core
colon directive rules remain limited to `textDirective`, `leafDirective`, and
`containerDirective`.

## Enable Directives

```python
from wenmode import Wenmode
from wenmode.presets import commonmark
from wenmode.rules import ContainerDirective, LeafDirective, TextDirective

wenmode = Wenmode([
    *commonmark,
    TextDirective,
    LeafDirective,
    ContainerDirective,
])
```

If you already have a configured `Wenmode` instance, register directive rules
incrementally:

```python
from wenmode import Wenmode
from wenmode.rules import ContainerDirective, LeafDirective, TextDirective

wenmode = Wenmode()
wenmode.register_rules([
    TextDirective,
    LeafDirective,
    ContainerDirective,
])
```

Text directives are inline:

```markdown
:abbr[HTML]{title="HyperText Markup Language"}
```

Leaf directives are block directives without body content:

```markdown
::toc[On this page]{min=2 max=3}
```

Container directives hold Markdown content:

```markdown
:::note[Important]
Read this first.
:::
```

All three rules use mdast-compatible node names:

- `TextDirective` creates `textDirective`.
- `LeafDirective` creates `leafDirective`.
- `ContainerDirective` creates `containerDirective`.

### Directive attributes

Directive heads can include labels and attributes. Attribute shortcuts map
`#id` to `id` and `.class` to `class`.

```markdown
:::note[Title]{#intro .wide data-kind=guide}
Body.
:::
```

Parsed directive nodes store the directive name, optional attributes, and child
nodes. Container directive labels are stored as the first paragraph child with
`data={"directiveLabel": True}`.

## HTML directive renderers

Register HTML directive renderers on `Wenmode` or pass them to `HTMLRenderer`.

```python
from wenmode import Wenmode
from wenmode.directives import Admonition
from wenmode.presets import commonmark
from wenmode.rules import ContainerDirective

wenmode = Wenmode([*commonmark, ContainerDirective])
wenmode.register_directive_renderer(Admonition())
text = '''
:::note[Title]
Body.
:::
'''

html = wenmode.render(text)
```

`register_directive_renderer()` requires an `HTMLRenderer`, because directive
renderers produce HTML.

You can also pass directive renderers at construction time:

```python
from wenmode import Wenmode
from wenmode.directives import Abbreviation, Admonition, Details, Figure, TableOfContents
from wenmode.presets import commonmark
from wenmode.rules import AtxHeading, ContainerDirective, LeafDirective

wenmode = Wenmode(
    [*commonmark, AtxHeading(id_transform=True), LeafDirective, ContainerDirective],
    directives=[Abbreviation(), Admonition(), Details(), Figure(), TableOfContents()],
)
```

Choose this construction-time form when the directive set is part of your
application's Markdown policy. Use `register_directive_renderer()` when a test
or integration needs to add one renderer to an already configured instance.

## Built-in directive renderers

### Abbreviation

`Abbreviation` renders text directives named `abbr` with a `title` attribute as
`<abbr>` elements.

```python
from wenmode.directives import Abbreviation

Abbreviation()
```

```markdown
:abbr[HTML]{title="HyperText Markup Language"}
```

### Admonition

`Admonition` renders container directives such as `note`, `tip`, `caution`, and
`danger` as `<aside>` elements with admonition classes.

```python
from wenmode.directives import Admonition

Admonition()
Admonition(names=['warning', 'important'])
```

### Details

`Details` renders `details` container directives as native HTML
`<details>` elements. The directive label becomes a `<summary>`.

```python
from wenmode.directives import Details

Details()
```

```markdown
:::details[Advanced options]{open}
Hidden content.
:::
```

### Figure

`Figure` renders `figure` container directives as `<figure>` with an optional
`<figcaption>` from the directive label.

```python
from wenmode.directives import Figure

Figure()
```

```markdown
:::figure[Architecture diagram]{src="/architecture.png" alt="System architecture"}
The parser builds an AST before rendering.
:::
```

### TableOfContents

`TableOfContents` renders a `toc` leaf directive from heading IDs already
present in the parsed tree. Use heading rules with `id_transform=True` when you
want Wenmode to create those heading IDs.

```python
from wenmode import HTMLRenderer, Parser
from wenmode.directives import TableOfContents
from wenmode.rules import AtxHeading, LeafDirective

parser = Parser([AtxHeading(id_transform=True), LeafDirective])
text = '''
::toc{min=2 max=3}

# Title

## Usage
'''

root = parser.parse(text)
html = HTMLRenderer(directives=[TableOfContents()]).render(root)
```

You can also collect and render a table of contents manually from the AST.

```python
from wenmode import HTMLRenderer, Parser
from wenmode.headings import Slugger, add_heading_ids
from wenmode.presets import commonmark
from wenmode.toc import collect_toc, render_toc_html

markdown = '''# Title
## Usage
### Options
### Example
'''
root = Parser(commonmark).parse(markdown)
add_heading_ids(root, slugger=Slugger(), min_depth=2)

toc = collect_toc(root, min_depth=2, max_depth=3)
html = render_toc_html(toc) + HTMLRenderer().render(root)
```
