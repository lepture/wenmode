(directives)=
# Directives

```{rst-class} lead
Use directive syntax and directive renderers to add structured Markdown
extensions.
```

---

Directives are parsed by rules and rendered by optional renderer plugins. These
are separate steps:

1. Enable directive syntax rules so the parser creates directive nodes.
2. Register directive renderers when you want special HTML output.

Without a matching HTML directive renderer, Wenmode falls back to rendering the
directive children.

## Two directive families

Wenmode supports two related directive syntax families.

The first family is `TextDirective`, `LeafDirective`, and `ContainerDirective`.
These follow the mdast directive model used by
[`mdast-util-directive`](https://github.com/syntax-tree/mdast-util-directive)
and remark directives: one colon for text directives, two colons for leaf block
directives, and three or more colons for container block directives. They create
mdast-compatible `textDirective`, `leafDirective`, and `containerDirective`
nodes.

The second family is `FencedDirective` and `Role`. These follow the
[MyST Parser roles and directives syntax](https://myst-parser.readthedocs.io/en/latest/syntax/roles-and-directives.html):
fenced directives use code-fence syntax with `{name}`, and roles use
`` {name}`content` ``. Wenmode maps them onto the same AST node types:
`FencedDirective` creates `containerDirective`, and `Role` creates
`textDirective`.

## mdast-style directives

```python
from wenmode import Parser
from wenmode.rules import ContainerDirective, LeafDirective, TextDirective

parser = Parser([
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

## MyST-style directives and roles

Fenced directives use code-fence-style syntax and serialize back to container
directives with `MarkdownRenderer`.

```python
from wenmode import Parser
from wenmode.rules import FencedDirective, Role

parser = Parser([FencedDirective, Role])
```

````markdown
```{note} Important
:class: warning

Read this first.
```
````

Roles are inline:

```markdown
{iconify}`devicon:pypi`
```

`FencedDirective` creates a `containerDirective` node. Its first-line argument
becomes the directive label, and `:key: value` option lines become attributes.

`Role` creates a `textDirective` node. The role name becomes the directive
`name`, and the backtick content becomes children.

## HTML directive renderers

Register HTML directive renderers on `Wenmode` or pass them to `HTMLRenderer`.

```python
from wenmode import Wenmode
from wenmode.directives import Admonition
from wenmode.rules import ContainerDirective

wenmode = Wenmode([ContainerDirective])
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
from wenmode.directives import Abbreviation, Admonition, Figure, TableOfContents
from wenmode.rules import AtxHeading, ContainerDirective, LeafDirective

wenmode = Wenmode(
    [AtxHeading(id_transform=True), LeafDirective, ContainerDirective],
    directives=[Abbreviation(), Admonition(), Figure(), TableOfContents()],
)
```

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

### Figure

`Figure` renders `figure` container directives as `<figure>` with an optional
`<figcaption>` from the directive label.

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
