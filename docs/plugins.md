(plugins)=
# Plugins

```{rst-class} lead
Enable non-standard Markdown syntax with explicit Wenmode plugins.
```

---

Plugins are feature modules that install parser rules and renderer handlers
together. Use them when syntax creates nodes outside the CommonMark, GFM, or
mdast directive surface.

Most applications use plugins in addition to a preset:

```python
from wenmode import Wenmode
from wenmode.presets import github
from wenmode.plugins import math

wenmode = Wenmode(github, plugins=[math])
```

Use a plugin when you want a complete feature. Use individual rules when you
are deliberately building a small dialect and already know which parser
behavior you need.

## Using Plugins

Import a plugin module from `wenmode.plugins` and pass it to `Wenmode` with the
`plugins` argument. During initialization, Wenmode calls each plugin's
`setup(wenmode, **options)` function with no extra options.

```python
from wenmode import Wenmode
from wenmode.plugins import math

wenmode = Wenmode(plugins=[math])

assert wenmode.render('Inline $x + y$.\n') == (
    '<p>Inline <span class="math math-inline">x + y</span>.</p>\n'
)
```

Install multiple plugins by listing them:

```python
from wenmode import Wenmode
from wenmode.plugins import mark, superscript

wenmode = Wenmode(plugins=[mark, superscript])
```

Some plugins accept setup options. For example, `math` can install only inline
or block syntax. Install those plugins with `use()` when you need to pass
options:

```python
from wenmode import Wenmode
from wenmode.plugins import math

inline_math = Wenmode().use(math, block=False)
block_math = Wenmode().use(math, inline=False)
```

Use `Wenmode.use(plugin, **options)` when you need to install a plugin after the
instance already exists. It returns the same `Wenmode` instance, so existing
chain-style setup remains supported.

## Built-In Plugins

| Plugin | Enables |
| --- | --- |
| `wenmode.plugins.abbr` | Abbreviation definitions and `abbreviation` nodes |
| `wenmode.plugins.definition_list` | Definition list syntax and nodes |
| `wenmode.plugins.fenced_directive` | MyST-style fenced directives, rendered as `containerDirective` nodes |
| `wenmode.plugins.frontmatter` | Top-level `---` front matter stored on `root.data["frontmatter"]` |
| `wenmode.plugins.inline_role` | MyST-style inline roles, rendered as `textDirective` nodes |
| `wenmode.plugins.insert` | `insert` inline nodes |
| `wenmode.plugins.mark` | `mark` inline nodes |
| `wenmode.plugins.math` | Display and inline math nodes |
| `wenmode.plugins.ruby` | Ruby annotation nodes |
| `wenmode.plugins.spoiler` | Block and inline spoiler nodes |
| `wenmode.plugins.subscript` | `subscript` inline nodes |
| `wenmode.plugins.superscript` | `superscript` inline nodes |

Each plugin also registers default HTML, Markdown, or RST renderer handlers when
the feature has a standard representation in Wenmode's built-in renderers.

## Front Matter

The `frontmatter` plugin consumes top-level `---` front matter before normal
Markdown block parsing and stores the parsed value on the root node. It does not
emit a child node. HTML output ignores front matter by default, Markdown output
serializes it back to a `---` block, and RST output renders flat metadata as a
docinfo field list.

```python
from wenmode import MarkdownRenderer, RSTRenderer, Wenmode
from wenmode.plugins import frontmatter

source = '---\ntitle: Hello\n---\n\n# Hi\n'

html = Wenmode(plugins=[frontmatter])
root = html.parse(source)
assert root.data == {'frontmatter': {'title': 'Hello'}}
assert html.render_node(root) == '<h1>Hi</h1>\n'

markdown = Wenmode(renderer=MarkdownRenderer(), plugins=[frontmatter])
assert markdown.render(source) == source

rst = Wenmode(renderer=RSTRenderer(), plugins=[frontmatter])
assert rst.render(source) == ':title: Hello\n\nHi\n==\n'
```

The default loader and dumper handle simple scalar `key: value` lines. Pass
custom callbacks when your application wants YAML or another metadata format.
The `load` callback receives only the text between the opening and closing
fences:

```python
from wenmode import Wenmode
from wenmode.plugins import frontmatter


def load_meta(source: str) -> dict[str, str]:
    return {'raw': source}


def dump_meta(value: object) -> str | None:
    if not isinstance(value, dict):
        return None
    return str(value['raw'])


wenmode = Wenmode().use(frontmatter, load=load_meta, dump=dump_meta, data_key='meta')
```

## Fenced Directives And Roles

The `fenced_directive` and `inline_role` plugins provide MyST-style directive
syntax. They do not create new plugin-specific node types. Instead, they map
onto the same mdast directive nodes documented in {ref}`directives`.

```python
from wenmode import Wenmode
from wenmode.plugins import fenced_directive, inline_role

wenmode = Wenmode(plugins=[fenced_directive, inline_role])
```

Fenced directives use code-fence-style syntax:

````markdown
```{note} Important
:class: warning

Read this first.
```
````

The fenced directive plugin creates a `containerDirective` node. Its first-line
argument becomes the directive label, `:key: value` option lines become
attributes, and body content is parsed as Markdown.

Inline roles use MyST-style role syntax:

```markdown
{iconify}`devicon:pypi`
```

The inline role plugin creates a `textDirective` node. The role name becomes the
directive `name`, and the backtick content becomes children.

After these plugins create directive nodes, HTML output still depends on
directive renderers. Register directive renderers the same way you would for
mdast-style directives.

Use these plugins when you want MyST-style syntax. Use the core
`TextDirective`, `LeafDirective`, and `ContainerDirective` rules when you want
mdast directive syntax with colon markers.

## Creating Plugins

A custom plugin is a module or object with a `setup(wenmode, **options)`
function. Inside `setup()`, register parser rules, renderer handlers, directive
renderers, or any combination of them.

```python
from wenmode import Wenmode
from wenmode.rules import Emphasis


class MyPlugin:
    def setup(self, wenmode: Wenmode, **options) -> None:
        wenmode.register_rule(Emphasis)


wenmode = Wenmode([], plugins=[MyPlugin()])
```

For non-trivial syntax, define the node, rule, render handlers, and `setup()`
together. See {ref}`custom-plugins` for a complete custom plugin walkthrough.
