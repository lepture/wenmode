(reference-extension-inlines)=
# Plugin inline rules

```{rst-class} lead
Inline syntax provided by built-in plugins.
```

---

Enable these features with `Wenmode(..., plugins=[...])` from `wenmode.plugins`. For
setup options and renderer behavior, see {ref}`plugins`.

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

`wenmode.plugins.inline_spoiler` parses spoiler spans delimited by `>!` and `!<`.

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

## Inline Math Plugin

`wenmode.plugins.inline_math` parses inline math delimited by `$`.

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
