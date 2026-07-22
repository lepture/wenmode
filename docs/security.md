---
description: Configure Wenmode HTML escaping, URL sanitization, raw HTML rules, trusted passthrough, and safe settings for user-authored Markdown.
---

(security)=
# Security

```{rst-class} lead
Understand Wenmode's default HTML escaping, URL sanitization, and raw HTML
controls.
```

---

Wenmode parses Markdown into an AST and then renders the AST. The renderer
controls most security behavior. The enabled rules also control whether raw HTML
enters the AST.

For untrusted content, use the default `Wenmode()` or `Wenmode(github)` with the
default `HTMLRenderer()`. Before you change renderer options, identify the code
that validates raw HTML and URLs in your application.

## Threat model

The default HTML path is for user-authored Markdown. It prevents raw HTML from
executing and omits unsafe link targets from active attributes. It is not a full
HTML sanitizer. If your application accepts raw HTML from untrusted users,
sanitize that HTML before or after Wenmode.

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

## Security profiles

Choose the profile that permits only the syntax required by the Markdown source.

| Scenario | Parser rules | Renderer | Notes |
| --- | --- | --- | --- |
| Public comments, issue text, chat, or profile Markdown | default `Wenmode()` or a preset without extra raw HTML rules | `HTMLRenderer()` | Escapes raw HTML and removes unsafe URL attributes. |
| Product docs written by trusted maintainers | `commonmark` or `github` | `HTMLRenderer(escape=False)` only if raw HTML is intentional | Keep an HTML sanitizer in the publishing pipeline if authors can paste arbitrary HTML. |
| CMS content sanitized before rendering | rules that match the CMS dialect | `HTMLRenderer(escape=False, sanitize_urls=False)` only after upstream validation | Wenmode will not re-sanitize trusted HTML or URLs in this mode. |
| Plain-text-only Markdown fields | custom rule list without `HtmlBlock` and `RawHtml` | `HTMLRenderer()` | Raw HTML syntax stays as text in the AST and renders escaped. |
| Streaming untrusted Markdown | `streaming` preset | `HTMLRenderer()` | Direct links work, reference-style links stay as text, unsafe URLs are sanitized. |

For untrusted content, do not use `escape=False` or `sanitize_urls=False` unless
a separate sanitizer or policy check has accepted the HTML and URLs.

## Restoring serialized AST data

Treat mappings passed to `wenmode.ast.from_ast()` as input, even when they
already look like an AST. By default, Wenmode validates structural fields such
as heading depth and ordered-list start values, and rejects parser-internal HTML
escaping metadata. This prevents external data from claiming that HTML was
already escaped by Wenmode.

The same checks apply to core `html` nodes, registered `htmlContainer` nodes,
and generic nodes using the reserved `htmlContainer` type. Other unknown node
types keep their extension data.

Restoration also applies default resource budgets to serialized AST mappings:
root node depth is `1`, each nested node mapping increases depth by `1`, and
each restored node mapping counts against the node budget. The defaults are
`max_depth=100` and `max_nodes=100_000`. These limits apply to built-in,
plugin, and generic unknown nodes.

Pass `max_depth=None` or `max_nodes=None` only across a trusted input boundary.
Disabling one budget does not disable the other budget, reference-cycle
detection, or structural validation. Cycles through node children, `data`, or
extension fields are always rejected.

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
trusted or another component has sanitized it.

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

This passes raw HTML nodes through the renderer. It does not sanitize HTML.

Unknown or custom literal nodes render string values as escaped text unless an
HTML handler is registered for their node type. Even with
`HTMLRenderer(escape=False)`, custom extensions that produce markup need an
explicit HTML handler.

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

The allowed URL schemes are `http`, `https`, `irc`, `ircs`, `mailto`, and `tel`.
Relative URLs are also allowed. Use `HTMLRenderer(sanitize_urls=False)` only
when another component validates URLs before rendering.

## Recommended settings

For untrusted Markdown, keep the default `HTMLRenderer()` settings. If you do
not need raw HTML in the AST at all, also remove `HtmlBlock` and `RawHtml` from
the rule list as shown below.

For trusted Markdown, `HTMLRenderer(escape=False)` can preserve raw HTML output.
Use it only when the source is controlled by your application or has already
passed through an HTML sanitizer.

Do not treat `escape=False` as a sanitizer setting. It is an output passthrough
setting for content you have already decided to trust.

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
from wenmode.presets import commonmark, create_preset
from wenmode.rules import HtmlBlock, RawHtml

safe_rules = create_preset(commonmark, remove=[HtmlBlock, RawHtml])
wen = Wenmode(safe_rules)
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
