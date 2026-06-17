# Security

Wenmode parses Markdown into an AST and then renders that AST. Security behavior
comes mostly from the renderer you choose and the rules you enable.

## Default HTML output

`Wenmode()` uses `HTMLRenderer()` by default. That renderer escapes text and raw
HTML nodes before writing HTML output.

```python
from wenmode import Wenmode

wenmode = Wenmode()
html = wenmode.render('<script>alert(1)</script>\n')

assert html == '&lt;script&gt;alert(1)&lt;/script&gt;\n'
```

Use this default when rendering user-authored Markdown into pages where raw HTML
must not execute.

## Allowing raw HTML

Construct `HTMLRenderer` with `escape=False` only when the Markdown source is
trusted or sanitized elsewhere.

```python
from wenmode import HTMLRenderer, Wenmode

wenmode = Wenmode(renderer=HTMLRenderer(escape=False))
html = wenmode.render('<span>trusted</span>\n')

assert html == '<p><span>trusted</span></p>\n'
```

This allows raw HTML nodes to pass through the renderer. It does not sanitize
HTML for you.

## URL sanitization

`HTMLRenderer` sanitizes link and image URLs by default. URLs with an unsafe
scheme are rendered without `href` or `src`.

```python
from wenmode import Wenmode

wenmode = Wenmode()
html = wenmode.render('[click](javascript:alert(1))\n')

assert html == '<p><a>click</a></p>\n'
```

Allowed URL schemes are `http`, `https`, `irc`, `ircs`, `mailto`, and `tel`.
Relative URLs are allowed. Use `HTMLRenderer(sanitize_urls=False)` only when URL
validation is handled before rendering.

## Disallowed HTML tags

The `github` preset configures HTML block and inline HTML handling with GitHub's
disallowed HTML tag list. Matching tags are escaped during parsing before they
reach the renderer.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
html = wenmode.render('<script>alert(1)</script>\n')

assert html == '&lt;script>alert(1)&lt;/script>\n'
```

This is useful when you want GFM-compatible handling of raw HTML. Keep the
default renderer escaping enabled unless your application has a separate HTML
sanitization layer.

## Rule-level control

If you do not want raw HTML syntax to become `html` AST nodes at all, use a
custom rule list that excludes `HtmlBlock` and `RawHtml`.

```python
from wenmode import Wenmode
from wenmode.presets import commonmark
from wenmode.rules import HtmlBlock, RawHtml

rules = [rule for rule in commonmark if rule not in {HtmlBlock, RawHtml}]
wenmode = Wenmode(rules)

html = wenmode.render('<span>text</span>\n')
assert html == '<p>&lt;span&gt;text&lt;/span&gt;</p>\n'
```

The rendered HTML is the same in this simple example because the default
renderer also escapes raw HTML nodes, but the AST shape is different: without
`HtmlBlock` and `RawHtml`, the input remains text instead of HTML nodes.
