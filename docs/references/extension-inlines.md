(reference-extension-inlines)=
# Extension inline rules

```{rst-class} lead
Inline extension rules for GFM, mdast directives, and built-in plugins.
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

## Mark Plugin

`wenmode.plugins.mark` parses highlighted text delimited by `==`.

```markdown
==marked==
```

Output node is `MarkNode`, and its AST is:

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

## Insert Plugin

`wenmode.plugins.insert` parses inserted text delimited by `^^`.

```markdown
^^inserted^^
```

Output node is `InsertNode`, and its AST is:

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

## Superscript Plugin

`wenmode.plugins.superscript` parses caret-delimited superscript spans.

```markdown
2^10^
```

Output node is `SuperscriptNode`, and its AST is:

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

## Subscript Plugin

`wenmode.plugins.subscript` parses tilde-delimited subscript spans.

```markdown
H~2~O
```

Output node is `SubscriptNode`, and its AST is:

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

## Ruby Plugin

`wenmode.plugins.ruby` parses ruby annotation syntax.

```markdown
[漢字(kanji)]
```

Output node is `RubyNode`, and its AST is:

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

## Spoiler Plugin

`wenmode.plugins.spoiler` parses spoiler spans delimited by `>!` and `!<`.

```markdown
>! secret !<
```

Output node is `InlineSpoilerNode`, and its AST is:

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

## Math Plugin

`wenmode.plugins.math` parses inline math delimited by `$`.

```markdown
$x + y$
```

Output node is `InlineMathNode`, and its AST is:

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

## Inline Role Plugin

`wenmode.plugins.inline_role` parses MyST-style inline roles.

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
