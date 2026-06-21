---
title: Wenmode MkDocs Example
layout: landing
---

# Wenmode MkDocs Example

This page is rendered by Wenmode before MkDocs builds the final HTML page.

:::note[Rendered directive]
Colon directives are parsed by Wenmode's built-in directive rules.
:::

```{warning} Fenced directive
:class: local

MyST-style fenced directives are handled by Wenmode's fenced directive plugin.
```

## Table

| Feature | Status |
| --- | --- |
| GFM table | Works |
| Task list | Works |

- [x] GitHub-style task list
- [ ] Remaining integration polish
