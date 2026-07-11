(security)=
# Security

```{rst-class} lead
Understand Wenmode's default HTML escaping, URL sanitization, and raw HTML
controls.
```

---

Wenmode parses Markdown into an AST and then renders that AST. Security behavior
comes mostly from the renderer you choose and the rules you enable.

For untrusted user content, the safest starting point is the default
`Wenmode()` or `Wenmode(github)` with the default `HTMLRenderer()`. Change
renderer safety options only after you know where raw HTML and URLs are
validated in your application.

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

## Restoring serialized AST data

Treat mappings passed to `wenmode.ast.from_ast()` as input,
even when they already have an AST shape. The safe default validates common
structural fields, including heading depth and ordered-list start values, and
rejects parser-internal HTML escaping metadata, so an external mapping cannot
claim that its HTML value was already escaped by Wenmode. This applies to
concrete core `html` nodes and concrete `htmlContainer` nodes, as well as
generic nodes using the reserved `htmlContainer` type when the plugin node
class was not registered. Unrelated unknown node types retain their extension
data.

Restoration also applies default resource budgets to serialized AST mappings:
root node depth is `1`, each nested node mapping increases depth by `1`, and
each restored node mapping counts against the node budget. The defaults are
`max_depth=100` and `max_nodes=100_000`. These limits apply to built-in,
plugin, and generic unknown nodes.

Pass `max_depth=None` or `max_nodes=None` only after your application has
established a trusted input boundary for that specific budget. Disabling one
budget does not disable the other budget, reference-cycle detection, or
structural validation. Cycles through node children, `data`, or extension
fields are rejected by default and cannot be enabled.

These budgets are not byte-size limits on the serialized payload before it is
decoded. If your application accepts untrusted JSON or another serialized
format, reject oversized payloads before decoding when you also need a byte
limit.

If you serialize an AST produced by Wenmode and later restore that data within
the same trusted pipeline, pass `allow_internal_metadata=True` to preserve the
internal escaping decision. Do not enable this option for client-supplied AST
data. It is a trusted-input setting and does not replace HTML sanitization.

## Default HTML output

`Wenmode()` uses `HTMLRenderer()` by default. That renderer escapes text and raw
HTML nodes before writing HTML output.

```python
from wenmode import Wenmode

wen = Wenmode()
text = '''
<script>alert(1)</script>
'''
expected = '''
&lt;script&gt;alert(1)&lt;/script&gt;
'''

html = wen.render(text)

assert html == expected.lstrip()
```

Use this default when rendering user-authored Markdown into pages where raw HTML
must not execute.

## Allowing raw HTML

Construct `HTMLRenderer` with `escape=False` only when the Markdown source is
trusted or sanitized elsewhere.

```python
from wenmode import HTMLRenderer, Wenmode

wen = Wenmode(renderer=HTMLRenderer(escape=False))
text = '<span>trusted</span>'
expected = '''
<p><span>trusted</span></p>
'''

html = wen.render(text)

assert html == expected.lstrip()
```

This allows raw HTML nodes to pass through the renderer. It does not sanitize
HTML for you.

Unknown or custom literal nodes render their string values as escaped text
unless an HTML handler is registered for their node type. This boundary also
applies when `HTMLRenderer(escape=False)` enables passthrough for concrete
`html` nodes; custom extensions that produce markup must register an explicit
HTML handler.

## URL sanitization

`HTMLRenderer` sanitizes link and image URLs by default. URLs with an unsafe
scheme are rendered without `href` or `src`.

```python
from wenmode import Wenmode

wen = Wenmode()
text = '[click](javascript:alert(1))'
expected = '''
<p><a>click</a></p>
'''

html = wen.render(text)

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

Do not treat `escape=False` as a sanitizer setting. It is an output passthrough
setting for content you have already decided to trust.

## Security profiles

Use the narrowest profile that matches the source of the Markdown.

| Scenario | Parser rules | Renderer | Notes |
| --- | --- | --- | --- |
| Public comments, issue text, chat, or profile Markdown | default `Wenmode()` or a preset without extra raw HTML rules | `HTMLRenderer()` | Escapes raw HTML and removes unsafe URL attributes. |
| Product docs written by trusted maintainers | `commonmark` or `github` | `HTMLRenderer(escape=False)` only if raw HTML is intentional | Keep an HTML sanitizer in the publishing pipeline if authors can paste arbitrary HTML. |
| CMS content sanitized before rendering | rules that match the CMS dialect | `HTMLRenderer(escape=False, sanitize_urls=False)` only after upstream validation | Wenmode will not re-sanitize trusted HTML or URLs in this mode. |
| Plain-text-only Markdown fields | custom rule list without `HtmlBlock` and `RawHtml` | `HTMLRenderer()` | Raw HTML syntax stays as text in the AST and renders escaped. |
| Streaming untrusted Markdown | `streaming` preset | `HTMLRenderer()` | Direct links work, reference-style links stay as text, unsafe URLs are sanitized. |

For untrusted content, avoid `escape=False` and `sanitize_urls=False` unless a
separate sanitizer or policy check has already accepted the HTML and URLs.

## Disallowed HTML tags

The `github` preset configures HTML block and inline HTML handling with GitHub's
disallowed HTML tag list. Matching tags are escaped during parsing before they
reach the renderer.

```python
from wenmode import Wenmode
from wenmode.presets import github

wen = Wenmode(github)
text = '''
<script>alert(1)</script>
'''
expected = '''
&lt;script&gt;alert(1)&lt;/script&gt;
'''

html = wen.render(text)

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
wen = Wenmode(rules)
text = '<span>text</span>'
expected = '''
<p>&lt;span&gt;text&lt;/span&gt;</p>
'''

html = wen.render(text)
assert html == expected.lstrip()
```

The rendered HTML is the same in this simple example because the default
renderer also escapes raw HTML nodes, but the AST shape is different: without
`HtmlBlock` and `RawHtml`, the input remains text instead of HTML nodes.
