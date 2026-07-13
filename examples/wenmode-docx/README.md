# wenmode-docx

`wenmode-docx` is a local example package that converts Markdown to DOCX.

It provides a `DOCXRenderer` for Wenmode. The renderer writes Wenmode nodes into
a Word document with `python-docx`. The implementation is intentionally small
and focused on the common document features you usually need first:

- headings
- paragraphs with emphasis, strong text, inline code, links, and images as text
- ordered, unordered, and task lists
- block quotes
- fenced and indented code blocks
- tables
- thematic breaks

## Usage

Run the example from this directory:

```bash
uv run wenmode-docx input.md output.docx
```

Or import it from Python:

```python
from pathlib import Path

from wenmode_docx import save_markdown_as_docx

save_markdown_as_docx(
    "# Report\n\nGenerated with **Wenmode**.\n",
    Path("report.docx"),
)
```

The converter returns a normal `docx.document.Document` object, so applications
can keep customizing the document before saving:

```python
from wenmode_docx import markdown_to_docx

document = markdown_to_docx("# Draft\n\nBody text.")
document.core_properties.title = "Draft"
document.save("draft.docx")
```

You can also use the renderer directly:

```python
from wenmode import Wenmode
from wenmode.presets import github
from wenmode_docx import DOCXRenderer

renderer = DOCXRenderer()
document = Wenmode(github, renderer=renderer).render("# Draft\n\nBody text.")
document.save("draft.docx")
```
