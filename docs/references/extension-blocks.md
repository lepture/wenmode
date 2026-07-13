(reference-extension-blocks)=
# Plugin block rules

```{rst-class} lead
Block-level and document-wide syntax provided by built-in plugins.
```

---

Enable these features with `Wenmode(..., plugins=[...])` from `wenmode.plugins`. For
setup options and renderer behavior, see {ref}`plugins`.

## HtmlContainer Plugin

`wenmode.plugins.html_container` replaces the CommonMark HTML block rule with a
non-standard container rule. When an opening HTML tag and its matching closing
tag each appear on their own line, the plugin parses the body as Markdown block
content.

```markdown
<div id="steps" hidden>
- one
- two
</div>
```

Output node is `HtmlContainerNode`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "htmlContainer",
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
                      "value": "one"
                    }
                  ]
                }
              ],
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
                      "value": "two"
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
      ],
      "name": "div",
      "attributes": {
        "id": "steps",
        "hidden": true
      },
      "opening": "<div id=\"steps\" hidden>",
      "closing": "</div>"
    }
  ]
}
```

The `opening` and `closing` fields preserve the original tag text for
round-tripping. The `attributes` field is a structured view for AST consumers:
quoted and unquoted values become strings, and boolean attributes become
`true`. Attribute names keep their source spelling, and attribute values are not
HTML entity decoded. If the same attribute name appears more than once, the last
parsed value is kept.

Raw-text tags such as `script`, `style`, `pre`, and `textarea` stay literal
`html` nodes. Self-closing tags, void tags, inline HTML, and unclosed tag pairs
also use the raw HTML fallback behavior.

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

## Block Math Plugin

`wenmode.plugins.block_math` parses display math fenced by `$$` markers.

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

## GitHub Alert Plugin

`wenmode.plugins.github_alert` parses top-level GitHub alert blockquotes whose
first line is one of `[!NOTE]`, `[!TIP]`, `[!IMPORTANT]`, `[!WARNING]`, or
`[!CAUTION]`.

```markdown
> [!NOTE]
> important *context*
```

The plugin replaces the already enabled `blockquote` rule. It does not enable
blockquote syntax by itself. HTML output defaults to GitHub-compatible
`markdown-alert` classes. Use `github_alert.configure(html_style="admonition")`
to render the same `<aside class="admonition ...">` structure as Wenmode's
admonition directive renderer.

Output node is `GithubAlertNode`, and its AST is:

```json
{
  "type": "root",
  "children": [
    {
      "type": "githubAlert",
      "name": "note",
      "children": [
        {
          "type": "paragraph",
          "children": [
            {
              "type": "text",
              "value": "important "
            },
            {
              "type": "emphasis",
              "children": [
                {
                  "type": "text",
                  "value": "context"
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

## Spoiler Plugin

`wenmode.plugins.block_spoiler` parses `>!`-prefixed spoiler blocks.

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

Output node is usually `ContainerDirective`, and its AST is:

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

Literal-body directive names create `LiteralDirective` nodes instead. The
default literal set includes `code-block`, so its body is kept as source text
instead of being parsed as Markdown:

````markdown
```{code-block} python
:caption: example.py

print("*not emphasis*")
```
````

```json
{
  "type": "root",
  "children": [
    {
      "type": "literalDirective",
      "value": "print(\"*not emphasis*\")\n",
      "name": "code-block",
      "argument": "python",
      "attributes": {
        "caption": "example.py"
      }
    }
  ]
}
```

Configure ``FencedDirectiveRule(fence=("`", "~", ":"))``, or pass
``fence=("`", "~", ":")`` to `wen.use(fenced_directive, ...)`, when your
dialect accepts MyST colon fences such as `:::{note}`.
