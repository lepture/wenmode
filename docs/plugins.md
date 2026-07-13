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
from wenmode.plugins import block_math, inline_math

wen = Wenmode(github, plugins=[inline_math, block_math])
```

Use this page to enable built-in plugins and understand their behavior. For
custom plugin authoring, see {ref}`custom-plugins`.

## Using Plugins

Import a plugin module from `wenmode.plugins` and pass it to `Wenmode` with the
`plugins` argument. During initialization, Wenmode calls each plugin's
`setup(wen, /)` function.

```python
from wenmode import Wenmode
from wenmode.plugins import inline_math

wen = Wenmode(plugins=[inline_math])

assert wen.render('Inline $x + y$.\n') == (
    '<p>Inline <span class="math math-inline">x + y</span>.</p>\n'
)
```

Install multiple plugins by listing them:

```python
from wenmode import Wenmode
from wenmode.plugins import mark, superscript

wen = Wenmode(plugins=[mark, superscript])
```

Some plugins accept configuration. Call `configure()` first and pass the
configured plugin to `Wenmode`:

```python
from wenmode import Wenmode
from wenmode.plugins import smartypants

wen = Wenmode(plugins=[smartypants.configure(dashes=False)])

assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” -- ok</p>\n'
```

Use `use()` when you need to install a plugin after an instance already exists:

```python
from wenmode import Wenmode
from wenmode.plugins import smartypants

wen = Wenmode().use(smartypants.configure(dashes=False))
```

`use()` returns the same `Wenmode` instance, so chain-style setup remains
supported.

## Built-In Plugins

| Plugin | Enables |
| --- | --- |
| `wenmode.plugins.abbr` | Abbreviation definitions and `abbreviation` nodes |
| `wenmode.plugins.block_spoiler` | Block spoiler containers |
| `wenmode.plugins.cjk_friendly` | CJK-friendly inline parsing behavior |
| `wenmode.plugins.definition_list` | Definition list syntax and nodes |
| `wenmode.plugins.fenced_directive` | MyST-style fenced directives, rendered as `containerDirective` or `literalDirective` nodes |
| `wenmode.plugins.frontmatter` | Top-level `---` front matter stored on `root.data["frontmatter"]` |
| `wenmode.plugins.html_container` | Standalone HTML tag pairs whose body is parsed as Markdown blocks |
| `wenmode.plugins.block_math` | Display math blocks |
| `wenmode.plugins.inline_math` | Inline math spans |
| `wenmode.plugins.inline_role` | MyST-style inline roles, rendered as `textDirective` nodes |
| `wenmode.plugins.inline_spoiler` | Inline spoiler spans |
| `wenmode.plugins.insert` | `insert` inline nodes |
| `wenmode.plugins.mark` | `mark` inline nodes |
| `wenmode.plugins.ruby` | Ruby annotation nodes |
| `wenmode.plugins.smartypants` | HTML smart punctuation rendering for quotes, dashes, and ellipses |
| `wenmode.plugins.subscript` | `subscript` inline nodes |
| `wenmode.plugins.superscript` | `superscript` inline nodes |

Each plugin also registers default HTML, Markdown, RST, or AsciiDoc renderer
handlers when the feature has a standard representation in Wenmode's built-in
renderers.
Plugins that introduce custom node types expose a `nodes` class list for
`wenmode.ast.from_ast()`; see {ref}`reference-nodes`.

## CJK-Friendly Parsing

The `cjk_friendly` plugin keeps default parsing for non-CJK text while making
inline behavior friendlier for Chinese, Japanese, and Korean prose. It allows
emphasis markers to open or close next to CJK characters and punctuation. When
the `extended_autolink` rule is already enabled, such as in the `github` preset,
it also leaves trailing CJK punctuation outside the generated link.

```python
from wenmode import Wenmode
from wenmode.plugins import cjk_friendly

wen = Wenmode(plugins=[cjk_friendly])

assert wen.render('**你好。**世界\n') == '<p><strong>你好。</strong>世界</p>\n'
```

```python
from wenmode import Wenmode
from wenmode.plugins import cjk_friendly
from wenmode.presets import github

wen = Wenmode(github, plugins=[cjk_friendly])

assert wen.render('请看 https://example.com。\n') == (
    '<p>请看 <a href="https://example.com">https://example.com</a>。</p>\n'
)
```

## Smart Punctuation

The `smartypants` plugin converts common ASCII punctuation in text nodes while
rendering HTML. It turns straight quotes into curly quotes, `--` and `---` into
en and em dashes, and `...` into an ellipsis. Code spans, fenced code, raw HTML,
link destinations, and image attributes are left unchanged. Non-HTML renderers
ignore this plugin.

```python
from wenmode import Wenmode
from wenmode.plugins import smartypants

wen = Wenmode(plugins=[smartypants])

assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” – ok</p>\n'
```

Use `configure()` to disable individual replacements:

```python
from wenmode import Wenmode
from wenmode.plugins import smartypants

wen = Wenmode(plugins=[smartypants.configure(dashes=False)])
```

## HTML Containers

The `html_container` plugin replaces the CommonMark `HtmlBlock` rule with a
non-standard `HtmlContainer` rule. Standalone HTML tag pairs become
`htmlContainer` parent nodes, and the content between the tags is parsed as
Markdown block content.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.plugins import html_container

wen = Wenmode(renderer=HTMLRenderer(escape=False), plugins=[html_container])

text = '''
<div>
- one
</div>
'''

result = '''
<div>
<ul>
<li>one</li>
</ul>
</div>
'''

assert wen.render(text.lstrip()) == result.lstrip()
```

The plugin keeps raw-text tags such as `script`, `style`, `pre`, and
`textarea` as literal `html` nodes. Self-closing tags, void tags, inline HTML,
and unclosed tag pairs also fall back to the normal raw HTML block behavior.
`htmlContainer` nodes keep the original opening and closing tag text and expose
parsed attributes for AST consumers.

HTML renderer escaping still applies to the container boundaries by default.
Use `HTMLRenderer(escape=False)` only for trusted or separately sanitized
content, the same as raw HTML nodes.

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


wen = Wenmode().use(frontmatter.configure(load=load_meta, dump=dump_meta, data_key='meta'))
```

## Fenced Directives And Roles

The `fenced_directive` and `inline_role` plugins provide MyST-style directive
syntax. Inline roles map onto `textDirective`, one of the mdast-compatible
directive nodes documented in {ref}`directives`. Fenced directives usually
create `containerDirective` nodes, and literal-body directives such as
`code-block` create `literalDirective` nodes.

```python
from wenmode import Wenmode
from wenmode.plugins import fenced_directive, inline_role

wen = Wenmode(plugins=[fenced_directive, inline_role])
```

Fenced directives use code-fence-style syntax:

````markdown
```{note} Important
:class: warning

Read this first.
```
````

The fenced directive plugin creates a `containerDirective` node by default. Its
first-line argument becomes the directive label, `:key: value` option lines
become attributes, and body content is parsed as Markdown.

Literal-body directives create `literalDirective` nodes so their body is kept as
source text instead of being parsed as Markdown. By default this applies to
`code-block`:

````markdown
```{code-block} python
:caption: example.py

print("*not emphasis*")
```
````

Pass `literal_names` to `configure()` when your application needs a different
set. Pass `fence` when your dialect also accepts other repeated fence
characters, such as MyST colon fences:

```python
from wenmode import Wenmode
from wenmode.plugins import fenced_directive

wen = Wenmode().use(
    fenced_directive.configure(
        literal_names={'code-block', 'sourcecode'},
        fence=('`', '~', ':'),
    )
)
```

Inline roles use MyST-style role syntax:

```markdown
{iconify}`devicon:pypi`
```

The inline role plugin creates a `textDirective` node. The role name becomes the
directive `name`, and the backtick content becomes children.

After these plugins create directive nodes, custom HTML output is still handled
through directive renderers registered by node type and directive name. Without
a matching renderer, text, leaf, and container directives fall back to their
child content. Literal directives fall back to escaped literal text, and
`code-block` has default code-block output in the HTML renderer.

Use these plugins when you want MyST-style syntax. Use the core
`TextDirective`, `LeafDirective`, and `ContainerDirective` rules when you want
mdast directive syntax with colon markers.

## Creating Plugins

A plugin is any module or object with a `setup(wen, /)` function:

```python
from wenmode import Wenmode
from wenmode.rules import Emphasis


def setup(wen: Wenmode, /) -> None:
    wen.register_rule(Emphasis)
```

Use {ref}`custom-plugins` when you need to define new parser rules, node types,
renderer handlers, setup options, or plugin state. Keep this page for choosing
and configuring plugins that ship with Wenmode.
