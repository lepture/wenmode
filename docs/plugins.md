(plugins)=
# Plugins

```{rst-class} lead
Enable non-standard Markdown syntax with explicit Wenmode plugins.
```

---

Plugins are feature modules that can register parser rules and renderer handlers
together. Use them when syntax creates nodes outside the CommonMark, GFM, or
mdast directive surface.

```python
from wenmode import Wenmode
from wenmode.presets import github
from wenmode.plugins import ruby

wenmode = Wenmode(github).use(ruby)

assert wenmode.render('[漢字(kanji)]\n') == '<p><ruby>漢字<rt>kanji</rt></ruby></p>\n'
```

Each plugin module exposes a `setup(wenmode, **options)` function.
`Wenmode.use()` accepts plugin modules or plugin objects, calls that function,
and returns the same `Wenmode` instance, so plugins can be chained:

```python
from wenmode import Wenmode
from wenmode.plugins import mark, superscript

wenmode = Wenmode().use(mark).use(superscript)
```

Available built-in plugins:

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

`math` and `spoiler` can install only one side of their syntax:

```python
from wenmode import Wenmode
from wenmode.plugins import math, spoiler

wenmode = (
    Wenmode()
    .use(math, block=False)
    .use(spoiler, inline=False)
)
```
