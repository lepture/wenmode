---
description: Enable GitHub-flavored Markdown features in Wenmode with the github preset and GitHub alert blockquotes with the github_alert plugin.
---

(recipes-github-flavored-markdown)=
# GitHub-flavored Markdown

```{rst-class} lead
Enable GitHub-flavored Markdown features with the `github` preset, then add
GitHub alert blockquotes when your product needs them.
```

---

## Use the GitHub preset

Use the `github` preset when you want tables, task list items, strikethrough,
bare URL autolinks, footnotes, and GFM disallowed HTML handling.

```python
from wenmode import Wenmode
from wenmode.presets import github

wen = Wenmode(github)
text = '''
- [x] done

| A | B |
| --- | --- |
| **x** | https://example.com |
'''

html = wen.render(text)

assert '<input checked="" disabled="" type="checkbox">' in html
assert '<table>' in html
assert '<a href="https://example.com">https://example.com</a>' in html
```

For exact preset membership, see {ref}`presets` and {ref}`rule-matrix`.

## Add GitHub alerts

GitHub alert blockquotes are provided by the `github_alert` plugin. Use it with
the `github` preset when your Markdown should support alert blocks such as
`[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, and `[!CAUTION]`.

```python
from wenmode import Wenmode
from wenmode.plugins import github_alert
from wenmode.presets import github

wen = Wenmode(github, plugins=[github_alert])
text = '''
> [!NOTE]
> **Read** this before deploying.
'''

html = wen.render(text)

assert '<div class="markdown-alert markdown-alert-note">' in html
assert '<p class="markdown-alert-title">Note</p>' in html
assert '<strong>Read</strong>' in html
```

When you want Wenmode's admonition HTML classes instead of GitHub's
`markdown-alert` classes, configure the plugin:

```python
from wenmode import Wenmode
from wenmode.plugins import github_alert
from wenmode.presets import github

wen = Wenmode(github, plugins=[github_alert.configure(html_style='admonition')])
text = '''
> [!WARNING]
> Check the migration notes.
'''

html = wen.render(text)

assert '<aside class="admonition admonition-warning">' in html
assert '<p class="admonition-title">Warning</p>' in html
```

The alert plugin replaces the enabled blockquote rule. It does not enable
blockquote syntax by itself, so pair it with `github`, `commonmark`, or an
explicit rule list that includes blockquotes.
