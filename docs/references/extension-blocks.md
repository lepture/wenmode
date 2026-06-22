(reference-extension-blocks)=
# Plugin block rules

```{rst-class} lead
Block-level and document-wide syntax provided by built-in plugins.
```

---

Enable these features with `Wenmode().use(...)` from `wenmode.plugins`. For
setup options and renderer behavior, see {ref}`plugins`.

## Frontmatter Plugin

`wenmode.plugins.frontmatter` consumes top-level `---` front matter and stores
the parsed metadata on the root node.

```markdown
---
title: Hello
---

# Hi
```

The plugin does not emit a front matter child node. The AST is:

```json
{
  "type": "root",
  "data": {
    "frontmatter": {
      "title": "Hello"
    }
  },
  "children": [
    {
      "type": "heading",
      "children": [
        {
          "type": "text",
          "value": "Hi"
        }
      ],
      "depth": 1
    }
  ]
}
```

With source positions enabled, child node positions still refer to the original
source document, including the consumed front matter lines.

HTML output ignores front matter by default. Markdown output serializes it back
to a top-level `---` block, and RST output renders flat metadata as docinfo
fields before the document body.

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
