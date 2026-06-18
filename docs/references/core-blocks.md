(reference-core-blocks)=
# Core block rules

```{rst-class} lead
Block-level rules for CommonMark-style document structure.
```

---

## AtxHeading

`AtxHeading` parses hash-prefixed ATX headings from level 1 through level 6.

```markdown
# Title
```

Output node is `Heading`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "heading",
      "children": [
        {
          "type": "text",
          "value": "Title"
        }
      ],
      "depth": 1
    }
  ]
}
```

Option example: use `AtxHeading(id_transform=True)` to add generated heading
IDs.

```markdown
# Hello World
```

```json
{
  "type": "root",
  "children": [
    {
      "type": "heading",
      "data": {
        "id": "hello-world"
      },
      "children": [
        {
          "type": "text",
          "value": "Hello World"
        }
      ],
      "depth": 1
    }
  ]
}
```

## SetextHeading

`SetextHeading` parses paragraph continuations followed by `===` or `---` as
level 1 or level 2 headings.

```markdown
Title
-----
```

Output node is `Heading`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "heading",
      "children": [
        {
          "type": "text",
          "value": "Title"
        }
      ],
      "depth": 2
    }
  ]
}
```

Option example: use `SetextHeading(id_transform=True)` to add generated heading
IDs.

```markdown
Hello World
===========
```

```json
{
  "type": "root",
  "children": [
    {
      "type": "heading",
      "data": {
        "id": "hello-world"
      },
      "children": [
        {
          "type": "text",
          "value": "Hello World"
        }
      ],
      "depth": 1
    }
  ]
}
```

## ThematicBreak

`ThematicBreak` parses horizontal rules made from `---`, `***`, or `___`.

```markdown
---
```

Output node is `ThematicBreak`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "thematicBreak"
    }
  ]
}
```

## FencedCode

`FencedCode` parses fenced code blocks opened by backtick or tilde fences.

````markdown
```python
print(1)
```
````

Output node is `Code`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "code",
      "value": "print(1)\n",
      "lang": "python"
    }
  ]
}
```

## IndentedCode

`IndentedCode` parses code blocks indented by four spaces or one tab.

```markdown
    print(1)
```

Output node is `Code`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "code",
      "value": "print(1)\n"
    }
  ]
}
```

## HtmlBlock

`HtmlBlock` parses CommonMark HTML block starts.

```markdown
<div>Hi</div>
```

Output node is `Html`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "html",
      "value": "<div>Hi</div>\n"
    }
  ]
}
```

Option example: use `HtmlBlock(disallowed_tags=["script"])` to escape selected
tags during parsing.

```markdown
<script>alert(1)</script>
```

```json
{
  "type": "root",
  "children": [
    {
      "type": "html",
      "data": {
        "escaped": true
      },
      "value": "&lt;script>alert(1)&lt;/script>\n"
    }
  ]
}
```

## Blockquote

`Blockquote` parses `>`-prefixed blockquote containers.

```markdown
> *quote*
```

Output node is `Blockquote`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "blockquote",
      "children": [
        {
          "type": "paragraph",
          "children": [
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "quote"
                }
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

## List

`List` parses bullet and ordered lists.

```markdown
- *item*
```

Output nodes are `List` and `ListItem`, and their AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "list",
      "children": [
        {
          "type": "listItem",
          "children": [
            {
              "type": "paragraph",
              "children": [
                {
                  "type": "emphasis",
                  "children": [
                    {
                      "type": "text",
                      "value": "item"
                    }
                  ]
                }
              ]
            }
          ],
          "spread": false
        }
      ],
      "ordered": false,
      "spread": false
    }
  ]
}
```

Option example: use `List(task=True)` to parse GFM task list markers.

```markdown
- [x] done
- [ ] todo
```

```json
{
  "type": "root",
  "children": [
    {
      "type": "list",
      "children": [
        {
          "type": "listItem",
          "children": [
            {
              "type": "paragraph",
              "children": [
                {
                  "type": "text",
                  "value": "done"
                }
              ]
            }
          ],
          "checked": true,
          "spread": false
        },
        {
          "type": "listItem",
          "children": [
            {
              "type": "paragraph",
              "children": [
                {
                  "type": "text",
                  "value": "todo"
                }
              ]
            }
          ],
          "checked": false,
          "spread": false
        }
      ],
      "ordered": false,
      "spread": false
    }
  ]
}
```

