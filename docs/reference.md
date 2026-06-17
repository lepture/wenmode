# Reference

This page lists Wenmode's public rules and the nodes they produce. Each rule is
opt-in: the parser only recognizes syntax for the rules you enable.

AST examples are JSON-style output from `root.to_ast()`. The top-level shape is
always:

```json
{
  "type": "root",
  "children": []
}
```

Directive HTML can be replaced by registering directive renderers. Raw HTML is
escaped by the default `HTMLRenderer` unless you construct it with
`HTMLRenderer(escape=False)`.

## Node model

Wenmode nodes are mdast-compatible data objects. Core Markdown nodes use
mdast-style names and fields, and extensions follow the same conventions with
explicit node types.

| Node group | Node types |
| --- | --- |
| Document and containers | `root`, `paragraph`, `heading`, `blockquote`, `list`, `listItem` |
| Literals | `text`, `inlineCode`, `code`, `html`, `math`, `inlineMath` |
| Formatting | `emphasis`, `strong`, `delete`, `mark`, `insert`, `superscript`, `subscript` |
| Links and media | `link`, `image`, `break` |
| GFM and extensions | `table`, `tableRow`, `tableCell`, `footnoteReference`, `footnoteDefinition`, `abbreviation`, `definitionList`, `definitionTerm`, `definitionDescription` |
| Wenmode extensions | `ruby`, `inlineSpoiler`, `blockSpoiler` |
| Directives | `textDirective`, `leafDirective`, `containerDirective` |

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
---
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
===
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

## Table

`Table` parses GFM pipe tables.

```markdown
| A | B |
| :--- | ---: |
| *x* | y |
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

## Abbreviation

`Abbreviation` parses abbreviation definitions and rewrites matching text into
abbreviation nodes.

```markdown
The HTML spec.

*[HTML]: HyperText Markup Language
```

Output node is `Abbreviation`, and its AST is:

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

## DefinitionList

`DefinitionList` parses a paragraph followed by colon-prefixed definition
continuations.

```markdown
Apple
: *fruit*
```

Output nodes are `DefinitionList`, `DefinitionTerm`, and
`DefinitionDescription`, and their AST is:

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

## MathBlock

`MathBlock` parses display math fenced by `$$` markers.

```markdown
$$
x + y
$$
```

Output node is `Math`, and its AST is:

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

## BlockSpoiler

`BlockSpoiler` parses `>!`-prefixed spoiler blocks.

```markdown
>! hidden *thing*
```

Output node is `BlockSpoiler`, and its AST is:

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

## FencedDirective

`FencedDirective` parses MyST-style fenced directives.

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

## InlineCode

`InlineCode` parses inline code spans.

```markdown
`code`
```

Output node is `InlineCode`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "inlineCode",
          "value": "code"
        }
      ]
    }
  ]
}
```

## Emphasis

`Emphasis` parses emphasis and strong emphasis delimiters.

```markdown
*em* and **strong**
```

Output nodes are `Emphasis` and `Strong`, and their AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "emphasis",
          "children": [
            {
              "type": "text",
              "value": "em"
            }
          ]
        },
        {
          "type": "text",
          "value": " and "
        },
        {
          "type": "strong",
          "children": [
            {
              "type": "text",
              "value": "strong"
            }
          ]
        }
      ]
    }
  ]
}
```

## Link

`Link` parses inline links and, by default, reference-style links.

```markdown
[*label*](/url "Title")
```

Output node is `Link`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "link",
          "children": [
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "label"
                }
              ]
            }
          ],
          "url": "/url",
          "title": "Title"
        }
      ]
    }
  ]
}
```

Option example: use `Link(references=False)` when only inline links should be
resolved.

```markdown
[label][id]

[id]: /url
```

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "[label][id]"
        }
      ]
    },
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "[id]: /url"
        }
      ]
    }
  ]
}
```

## Image

`Image` parses inline images and, by default, reference-style images.

```markdown
![*alt*](/img.png "Title")
```

Output node is `Image`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "image",
          "url": "/img.png",
          "alt": "alt",
          "title": "Title"
        }
      ]
    }
  ]
}
```

Option example: use `Image(references=False)` when only inline images should be
resolved.

```markdown
![alt][id]

[id]: /img.png
```

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "![alt][id]"
        }
      ]
    },
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "[id]: /img.png"
        }
      ]
    }
  ]
}
```

## Autolink

`Autolink` parses angle-bracket URI and email autolinks.

```markdown
<https://example.com>
```

Output node is `Link`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "link",
          "children": [
            {
              "type": "text",
              "value": "https://example.com"
            }
          ],
          "url": "https://example.com"
        }
      ]
    }
  ]
}
```

## RawHtml

`RawHtml` parses inline HTML tags and comments.

```markdown
<span>hi</span>
```

Output node is `Html`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "html",
          "value": "<span>"
        },
        {
          "type": "text",
          "value": "hi"
        },
        {
          "type": "html",
          "value": "</span>"
        }
      ]
    }
  ]
}
```

Option example: use `RawHtml(disallowed_tags=["span"])` to escape selected
inline tags during parsing.

```markdown
<span>hi</span>
```

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "html",
          "data": {
            "escaped": true
          },
          "value": "&lt;span>"
        },
        {
          "type": "text",
          "value": "hi"
        },
        {
          "type": "html",
          "data": {
            "escaped": true
          },
          "value": "&lt;/span>"
        }
      ]
    }
  ]
}
```

## BackslashEscape

`BackslashEscape` parses backslash escapes for escapable punctuation.

```markdown
\*
```

Output node is `Text`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "*"
        }
      ]
    }
  ]
}
```

## CharacterReference

`CharacterReference` parses named and numeric character references.

```markdown
&copy;
```

Output node is `Text`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "©"
        }
      ]
    }
  ]
}
```

## HardBreak

`HardBreak` parses hard line breaks created with a trailing backslash or two
trailing spaces.

```markdown
line\
break
```

Output node is `Break`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "line"
        },
        {
          "type": "break"
        },
        {
          "type": "text",
          "value": "break"
        }
      ]
    }
  ]
}
```

## Strikethrough

`Strikethrough` parses single- or double-tilde deletion spans.

```markdown
~~delete~~
```

Output node is `Delete`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "delete",
          "children": [
            {
              "type": "text",
              "value": "delete"
            }
          ]
        }
      ]
    }
  ]
}
```

## ExtendedAutolink

`ExtendedAutolink` parses bare URL and email autolinks.

```markdown
https://example.com
```

Output node is `Link`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "link",
          "children": [
            {
              "type": "text",
              "value": "https://example.com"
            }
          ],
          "url": "https://example.com"
        }
      ]
    }
  ]
}
```

## Mark

`Mark` parses highlighted text delimited by `==`.

```markdown
==marked==
```

Output node is `Mark`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "mark",
          "children": [
            {
              "type": "text",
              "value": "marked"
            }
          ]
        }
      ]
    }
  ]
}
```

## Insert

`Insert` parses inserted text delimited by `^^`.

```markdown
^^inserted^^
```

Output node is `Insert`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "insert",
          "children": [
            {
              "type": "text",
              "value": "inserted"
            }
          ]
        }
      ]
    }
  ]
}
```

## Superscript

`Superscript` parses caret-delimited superscript spans.

```markdown
2^10^
```

Output node is `Superscript`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "2"
        },
        {
          "type": "superscript",
          "children": [
            {
              "type": "text",
              "value": "10"
            }
          ]
        }
      ]
    }
  ]
}
```

## Subscript

`Subscript` parses tilde-delimited subscript spans.

```markdown
H~2~O
```

Output node is `Subscript`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "text",
          "value": "H"
        },
        {
          "type": "subscript",
          "children": [
            {
              "type": "text",
              "value": "2"
            }
          ]
        },
        {
          "type": "text",
          "value": "O"
        }
      ]
    }
  ]
}
```

## Ruby

`Ruby` parses ruby annotation syntax.

```markdown
[漢字(kanji)]
```

Output node is `Ruby`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "ruby",
          "segments": [
            {
              "base": "漢字",
              "text": "kanji"
            }
          ]
        }
      ]
    }
  ]
}
```

## InlineSpoiler

`InlineSpoiler` parses spoiler spans delimited by `>!` and `!<`.

```markdown
>! secret !<
```

Output node is `InlineSpoiler`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "inlineSpoiler",
          "children": [
            {
              "type": "text",
              "value": "secret"
            }
          ]
        }
      ]
    }
  ]
}
```

## InlineMath

`InlineMath` parses inline math delimited by `$`.

```markdown
$x + y$
```

Output node is `InlineMath`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "inlineMath",
          "value": "x + y"
        }
      ]
    }
  ]
}
```

## TextDirective

`TextDirective` parses inline directives such as `:name[label]{attrs}`.

```markdown
:abbr[*HTML*]{title="HyperText Markup Language"}
```

Output node is `TextDirective`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "textDirective",
          "children": [
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "HTML"
                }
              ]
            }
          ],
          "name": "abbr",
          "attributes": {
            "title": "HyperText Markup Language"
          }
        }
      ]
    }
  ]
}
```

## Role

`Role` parses MyST-style inline roles.

```markdown
{abbr}`HTML`
```

Output node is `TextDirective`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "paragraph",
      "children": [
        {
          "type": "textDirective",
          "children": [
            {
              "type": "text",
              "value": "HTML"
            }
          ],
          "name": "abbr"
        }
      ]
    }
  ]
}
```
