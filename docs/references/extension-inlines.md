(reference-extension-inlines)=
# Extension inline rules

```{rst-class} lead
Inline extension rules for GFM, formatting, math, spoilers, ruby, and directives.
```

---

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

