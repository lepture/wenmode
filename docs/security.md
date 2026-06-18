(security)=
# Security

```{rst-class} lead
Understand Wenmode's default HTML escaping, URL sanitization, and raw HTML
controls.
```

---

Wenmode parses Markdown into an AST and then renders that AST. Security behavior
comes mostly from the renderer you choose and the rules you enable.

## Threat model

The default HTML path is designed for user-authored Markdown where raw HTML
should not execute and unsafe link targets should not be emitted as active
attributes. It is not a full HTML sanitizer for already-trusted raw HTML.

Keep these boundaries in mind:

- `HTMLRenderer()` escapes text and raw HTML nodes by default.
- URL sanitization removes unsafe `href` and `src` attributes from rendered
  links and images.
- Parser rules decide whether raw HTML syntax becomes `html` AST nodes or plain
  text.
- `HTMLRenderer(escape=False)` and `HTMLRenderer(sanitize_urls=False)` are
  trusted-input settings.
- If your application allows raw HTML from untrusted users, sanitize that HTML
  before or after Wenmode with an HTML sanitizer built for your threat model.

## Default HTML output

`Wenmode()` uses `HTMLRenderer()` by default. That renderer escapes text and raw
HTML nodes before writing HTML output.

```python
from wenmode import Wenmode

wenmode = Wenmode()
text = '''
<script>alert(1)</script>
'''
expected = '''
&lt;script&gt;alert(1)&lt;/script&gt;
'''

html = wenmode.render(text)

assert html == expected.lstrip()
```

Use this default when rendering user-authored Markdown into pages where raw HTML
must not execute.

## Allowing raw HTML

Construct `HTMLRenderer` with `escape=False` only when the Markdown source is
trusted or sanitized elsewhere.

```python
from wenmode import HTMLRenderer, Wenmode

wenmode = Wenmode(renderer=HTMLRenderer(escape=False))
text = '<span>trusted</span>'
expected = '''
<p><span>trusted</span></p>
'''

html = wenmode.render(text)

assert html == expected.lstrip()
```

This allows raw HTML nodes to pass through the renderer. It does not sanitize
HTML for you.

## URL sanitization

`HTMLRenderer` sanitizes link and image URLs by default. URLs with an unsafe
scheme are rendered without `href` or `src`.

```python
from wenmode import Wenmode

wenmode = Wenmode()
text = '[click](javascript:alert(1))'
expected = '''
<p><a>click</a></p>
'''

html = wenmode.render(text)

assert html == expected.lstrip()
```

Allowed URL schemes are `http`, `https`, `irc`, `ircs`, `mailto`, and `tel`.
Relative URLs are allowed. Use `HTMLRenderer(sanitize_urls=False)` only when URL
validation is handled before rendering.

## Recommended settings

For untrusted Markdown, keep the default `HTMLRenderer()` settings. If you do
not need raw HTML in the AST at all, also remove `HtmlBlock` and `RawHtml` from
the rule list as shown below.

For trusted Markdown, `HTMLRenderer(escape=False)` can preserve raw HTML output.
Use it only when the source is controlled by your application or has already
passed through an HTML sanitizer.

## Disallowed HTML tags

The `github` preset configures HTML block and inline HTML handling with GitHub's
disallowed HTML tag list. Matching tags are escaped during parsing before they
reach the renderer.

```python
from wenmode import Wenmode
from wenmode.presets import github

wenmode = Wenmode(github)
text = '''
<script>alert(1)</script>
'''
expected = '''
&lt;script>alert(1)&lt;/script>
'''

html = wenmode.render(text)

assert html == expected.lstrip()
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
text = '<span>text</span>'
expected = '''
<p>&lt;span&gt;text&lt;/span&gt;</p>
'''

html = wenmode.render(text)
assert html == expected.lstrip()
```

The rendered HTML is the same in this simple example because the default
renderer also escapes raw HTML nodes, but the AST shape is different: without
`HtmlBlock` and `RawHtml`, the input remains text instead of HTML nodes.
