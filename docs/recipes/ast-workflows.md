---
description: Work with Wenmode AST nodes by serializing mdast-compatible JSON or walking node objects directly.
---

(recipes-ast-workflows)=
# AST workflows

```{rst-class} lead
Use Wenmode's parsed tree as application data for storage, indexing,
diagnostics, or custom processing.
```

---

Use `Node.to_ast()` when another service or storage layer needs plain
dictionary data. Use `wenmode.ast` helpers when Python code should inspect node
objects directly.

## Convert the AST to JSON

`Node.to_ast()` returns plain Python dictionaries and lists, so you can
serialize the parsed tree with the standard `json` module.

```python
import json

from wenmode import Wenmode

text = 'A [link](https://example.com).'

root = Wenmode().parse(text)
payload = json.dumps(root.to_ast(), ensure_ascii=False)

assert '"type": "root"' in payload
assert '"url": "https://example.com"' in payload
```

For node shape details, see {ref}`reference-nodes`.

## Inspect AST nodes

Use `wenmode.ast` helpers when you want to inspect parsed node objects directly
instead of first converting them to dictionaries.

```python
from wenmode import Wenmode
from wenmode.ast import find_all, plain_text, walk
from wenmode.nodes import Heading
from wenmode.presets import github

text = '''
# Title

## Usage

A [link](https://example.com).
'''

root = Wenmode(github).parse(text)

headings = find_all(root, Heading)
links = find_all(root, 'link')
node_types = [node.type for node in walk(root)]

assert [plain_text(heading) for heading in headings] == ['Title', 'Usage']
assert links[0].url == 'https://example.com'
assert node_types[:3] == ['root', 'heading', 'text']
```
