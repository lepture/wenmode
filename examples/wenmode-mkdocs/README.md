# wenmode-mkdocs

This is a local MkDocs example that renders Markdown pages through Wenmode.
It is intended as a small bridge package in this repository and is not
published to PyPI.

Install the package from this directory when trying it locally:

```bash
uv run --directory examples/wenmode-mkdocs mkdocs build --strict
```

Enable the plugin in `mkdocs.yml`:

```yaml
plugins:
  - search
  - wenmode
```

The plugin uses MkDocs' `on_page_markdown` hook and returns Wenmode-rendered
HTML. MkDocs still runs its normal Python-Markdown step afterwards, but raw
HTML is preserved, which makes this useful as a compact example for replacing
page Markdown rendering in a documentation build. It currently demonstrates:

- GitHub-style Markdown through Wenmode's `github` preset.
- mdast-style colon directives such as `:::note[Title]`.
- MyST-style fenced directives such as ```` ```{note} Title ````.
- Wenmode HTML directive renderers for admonitions, details, figures, and TOC.
- Top-level front matter through Wenmode's `frontmatter` plugin.
