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

wenmode = Wenmode(github).use(math)
```

Use a plugin when you want a complete feature. Use individual rules when you
are deliberately building a small dialect and already know which parser
behavior you need.

## Using Plugins

Import a plugin module from `wenmode.plugins` and pass it to `Wenmode.use()`.
The method calls the plugin's `setup(wenmode, **options)` function and returns
the same `Wenmode` instance.

```python
from wenmode import Wenmode
from wenmode.plugins import math

wenmode = Wenmode().use(math)

assert wenmode.render('Inline $x + y$.\n') == (
    '<p>Inline <span class="math math-inline">x + y</span>.</p>\n'
)
```

Plugins can be chained:

```python
from wenmode import Wenmode
from wenmode.plugins import mark, superscript

wenmode = Wenmode().use(mark).use(superscript)
```

Some plugins accept setup options. For example, `math` can install only inline
or block syntax:

```python
from wenmode import Wenmode
from wenmode.plugins import math

inline_math = Wenmode().use(math, block=False)
block_math = Wenmode().use(math, inline=False)
```

## Built-In Plugins

| Plugin | Enables |
| --- | --- |
| `wenmode.plugins.abbr` | Abbreviation definitions and `abbreviation` nodes |
| `wenmode.plugins.definition_list` | Definition list syntax and nodes |
| `wenmode.plugins.fenced_directive` | MyST-style fenced directives, rendered as `containerDirective` nodes |
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

## Fenced Directives And Roles

The `fenced_directive` and `inline_role` plugins provide MyST-style directive
syntax. They do not create new plugin-specific node types. Instead, they map
onto the same mdast directive nodes documented in {ref}`directives`.

```python
from wenmode import Wenmode
from wenmode.plugins import fenced_directive, inline_role

wenmode = Wenmode().use(fenced_directive).use(inline_role)
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


wenmode = Wenmode([]).use(MyPlugin())
```

For non-trivial syntax, define the node, rule, render handlers, and `setup()`
together. See {ref}`custom-plugins` for a complete custom plugin walkthrough.
