(reference-core-inlines)=
# Core inline rules

```{rst-class} lead
Inline rules for links, media, code spans, HTML, escapes, and emphasis.
```

---

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

Use `RawHtml(comment_style="gfm")` when a custom rule list needs the stricter
GFM 0.29 inline HTML comment grammar. The default `comment_style="commonmark"`
matches the CommonMark preset.

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
