---
description: Render a table of contents from Wenmode Markdown with heading IDs, TOC helpers, and custom slug generation.
---

(recipes-table-of-contents)=
# Table of contents

```{rst-class} lead
Generate heading IDs, render tables of contents, and customize slug behavior for
documentation pages.
```

---

Use the `heading_ids` plugin and register the built-in `TableOfContents`
directive renderer when the table of contents should be declared inside the
Markdown document.

```python
from wenmode import Wenmode
from wenmode.directives import TableOfContents
from wenmode.plugins import heading_ids
from wenmode.rules import AtxHeading, LeafDirective

wen = Wenmode(
    [AtxHeading, LeafDirective],
    directives=[TableOfContents()],
    plugins=[heading_ids],
)
text = '''
::toc{min=2 max=3}

# Title

## Usage
'''

html = wen.render(text)

assert '<nav aria-label="Table of contents" class="toc">' in html
assert '<a href="#usage">Usage</a>' in html
assert '<h2 id="usage">Usage</h2>' in html
```

You can also build a table of contents manually when you want to place or style
it outside the Markdown document.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids
from wenmode.toc import collect_toc, render_toc_html

wen = Wenmode()
text = '''
# Title

## Usage
'''

root = wen.parse(text)
add_heading_ids(root, slugger=Slugger(), min_depth=2)

toc = collect_toc(root, min_depth=2, max_depth=3)
html = render_toc_html(toc) + HTMLRenderer().render(root)

assert '<a href="#usage">Usage</a>' in html
```

## Generate heading IDs only

Use the `heading_ids` plugin when you want Wenmode to add generated heading IDs
during parsing without rendering a table of contents.

```python
from wenmode import Wenmode
from wenmode.plugins import heading_ids
from wenmode.rules import AtxHeading

wen = Wenmode([AtxHeading], plugins=[heading_ids])
text = '# Hello World'
expected = '''
<h1 id="hello-world">Hello World</h1>
'''

html = wen.render(text)

assert html == expected.lstrip()
```

For already-parsed trees, use `add_heading_ids()`.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids

text = '''
# Title

## Usage
'''

root = Wenmode().parse(text)
add_heading_ids(root, slugger=Slugger(), min_depth=2)

html = HTMLRenderer().render(root)
assert '<h1>Title</h1>' in html
assert '<h2 id="usage">Usage</h2>' in html
```

## Customize heading slugs

Create a `Slugger` subclass when your product needs a different heading ID
format. Pass the slugger class to `heading_ids.configure()` for IDs generated
during parsing.

```python
from wenmode import Wenmode
from wenmode.headings import Slugger
from wenmode.plugins import heading_ids
from wenmode.rules import AtxHeading


class PrefixedSlugger(Slugger):
    name = 'prefixed'

    def slug(self, value: str) -> str:
        return 'section-' + super().slug(value)


wen = Wenmode([AtxHeading], plugins=[heading_ids.configure(PrefixedSlugger)])
html = wen.render('## Install\n\n## Install\n')

assert '<h2 id="section-install">Install</h2>' in html
assert '<h2 id="section-install-1">Install</h2>' in html
```

For already-parsed trees, pass an instance to `add_heading_ids()`.

```python
from wenmode import HTMLRenderer, Wenmode
from wenmode.headings import Slugger, add_heading_ids


class DocsSlugger(Slugger):
    name = 'docs'

    def slug(self, value: str) -> str:
        return 'docs-' + super().slug(value)


root = Wenmode().parse('## Usage\n')
add_heading_ids(root, slugger=DocsSlugger(), min_depth=2)

html = HTMLRenderer().render(root)

assert '<h2 id="docs-usage">Usage</h2>' in html
```
