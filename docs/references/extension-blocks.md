(reference-extension-blocks)=
# Extension block rules

```{rst-class} lead
Block-level and document-wide rules for GFM, mdast directives, and built-in
plugins.
```

---

## Table

`Table` parses GFM pipe tables.

```markdown
| A    | B    |
| :--- | ---: |
| *x*  | y    |
```

Output nodes are `Table`, `TableRow`, and `TableCell`, and their AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "table",
      "children": [
        {
          "type": "tableRow",
          "children": [
            {
              "type": "tableCell",
              "children": [
                {
                  "type": "text",
                  "value": "A"
                }
              ]
            },
            {
              "type": "tableCell",
              "children": [
                {
                  "type": "text",
                  "value": "B"
                }
              ]
            }
          ]
        },
        {
          "type": "tableRow",
          "children": [
            {
              "type": "tableCell",
              "children": [
                {
                  "type": "emphasis",
                  "children": [
                    {
                      "type": "text",
                      "value": "x"
                    }
                  ]
                }
              ]
            },
            {
              "type": "tableCell",
              "children": [
                {
                  "type": "text",
                  "value": "y"
                }
              ]
            }
          ]
        }
      ],
      "align": [
        "left",
        "right"
      ]
    }
  ]
}
```

## Footnote

`Footnote` parses inline footnote references and collects matching footnote
definitions with a document-wide transform.

```markdown
A note[^a].

[^a]: *Footnote*.
```

Output nodes are `FootnoteReference` and `FootnoteDefinition`, and their AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "A note"
        },
        {
          "type": "footnoteReference",
          "identifier": "a",
          "label": "a"
        },
        {
          "type": "text",
          "value": "."
        }
      ]
    },
    {
      "type": "footnoteDefinition",
      "children": [
        {
          "type": "paragraph",
          "children": [
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "Footnote"
                }
              ]
            },
            {
              "type": "text",
              "value": "."
            }
          ]
        }
      ],
      "identifier": "a",
      "label": "a"
    }
  ]
}
```

## Abbreviation Plugin

`wenmode.plugins.abbr` parses abbreviation definitions and rewrites matching
text into abbreviation nodes.

```markdown
The HTML spec.

*[HTML]: HyperText Markup Language
```

Output node is `AbbreviationNode`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "The "
        },
        {
          "type": "abbreviation",
          "children": [
            {
              "type": "text",
              "value": "HTML"
            }
          ],
          "title": "HyperText Markup Language"
        },
        {
          "type": "text",
          "value": " spec."
        }
      ]
    }
  ]
}
```

## DefinitionList Plugin

`wenmode.plugins.definition_list` parses a paragraph followed by colon-prefixed
definition continuations.

```markdown
Apple
: *fruit*
```

Output nodes are `DefinitionListNode`, `DefinitionTermNode`, and
`DefinitionDescriptionNode`, and their AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "definitionList",
      "children": [
        {
          "type": "definitionTerm",
          "children": [
            {
              "type": "text",
              "value": "Apple"
            }
          ]
        },
        {
          "type": "definitionDescription",
          "children": [
            {
              "type": "paragraph",
              "children": [
                {
                  "type": "emphasis",
                  "children": [
                    {
                      "type": "text",
                      "value": "fruit"
                    }
                  ]
                }
              ]
            }
          ],
          "spread": false
        }
      ]
    }
  ]
}
```

## Math Plugin

`wenmode.plugins.math` parses display math fenced by `$$` markers.

```markdown
$$
x + y
$$
```

Output node is `MathNode`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "math",
      "value": "x + y\n"
    }
  ]
}
```

## Spoiler Plugin

`wenmode.plugins.spoiler` parses `>!`-prefixed spoiler blocks.

```markdown
>! hidden *thing*
```

Output node is `BlockSpoilerNode`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "blockSpoiler",
      "children": [
        {
          "type": "paragraph",
          "children": [
            {
              "type": "text",
              "value": "hidden "
            },
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "thing"
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

## LeafDirective

`LeafDirective` parses leaf directives such as `::name[label]{attrs}`.

```markdown
::youtube[*Video*]{#abc}
```

Output node is `LeafDirective`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "leafDirective",
      "children": [
        {
          "type": "emphasis",
          "children": [
            {
              "type": "text",
              "value": "Video"
            }
          ]
        }
      ],
      "name": "youtube",
      "attributes": {
        "id": "abc"
      }
    }
  ]
}
```

## ContainerDirective

`ContainerDirective` parses colon-fenced block directives with optional labels
and attributes.

```markdown
:::note[Title]{.wide}
*Body*.
:::
```

Output node is `ContainerDirective`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "containerDirective",
      "children": [
        {
          "type": "paragraph",
          "data": {
            "directiveLabel": true
          },
          "children": [
            {
              "type": "text",
              "value": "Title"
            }
          ]
        },
        {
          "type": "paragraph",
          "children": [
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "Body"
                }
              ]
            },
            {
              "type": "text",
              "value": "."
            }
          ]
        }
      ],
      "name": "note",
      "attributes": {
        "class": "wide"
      }
    }
  ]
}
```

## Fenced Directive Plugin

`wenmode.plugins.fenced_directive` parses MyST-style fenced directives.

````markdown
```{note} Title
:class: wide

*Body*.
```
````

Output node is `ContainerDirective`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "containerDirective",
      "children": [
        {
          "type": "paragraph",
          "data": {
            "directiveLabel": true
          },
          "children": [
            {
              "type": "text",
              "value": "Title"
            }
          ]
        },
        {
          "type": "paragraph",
          "children": [
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "Body"
                }
              ]
            },
            {
              "type": "text",
              "value": "."
            }
          ]
        }
      ],
      "name": "note",
      "attributes": {
        "class": "wide"
      }
    }
  ]
}
```
