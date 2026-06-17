# Rules

Rules are opt-in and composable. A parser only recognizes syntax for rules that
you enable.

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading, Emphasis, InlineCode

wenmode = Wenmode([AtxHeading, InlineCode, Emphasis])
```

With this rule list, ATX headings, inline code, and emphasis are parsed. Other
Markdown syntax remains plain text unless another enabled rule handles it.

## Empty and custom rule sets

Pass an empty list when you want no Markdown rules enabled.

```python
from wenmode import Wenmode

wenmode = Wenmode([])
html = wenmode.render('# not a heading\n')
```

Pass classes or configured rule instances. Classes are instantiated
automatically, while instances let you choose rule options.

```python
from wenmode import Parser
from wenmode.rules import Image, Link

parser = Parser([
    Image(references=False),
    Link(references=False),
])
```

In this example, direct links and images are enabled, but reference-style links,
reference-style images, and reference definitions are not.

## Runtime registration

Rules can be registered after construction.

```python
from wenmode import Parser
from wenmode.rules import AtxHeading

parser = Parser([])
parser.register_rule(AtxHeading)
```

`register_rules()` accepts multiple rules:

```python
from wenmode.rules import AtxHeading, Emphasis, InlineCode

parser.register_rules([AtxHeading, InlineCode, Emphasis])
```

Rules are stored by name. Registering another rule with the same `name` replaces
the previous one.

## Rule categories

Wenmode has three parser rule categories:

- `BlockRule` parses block-level syntax such as headings, lists, tables, and
  fenced code.
- `ContinueRule` can turn an already-started paragraph into another node, such
  as a setext heading or definition list.
- `InlineRule` parses inline syntax such as links, inline code, directives, and
  formatting.

Some rules also attach root transforms. Transforms can collect definitions,
defer inline resolution until the whole document is known, or update parsed
nodes after block parsing is complete.

## Rule order

Block and inline rules are sorted by their `order` value. When multiple inline
rules match at the same position, the sorted rule order decides which rule wins.

Most custom rules can keep the default order. Set a custom `order` only when
your rule must run before or after another syntax with overlapping markers.

## Inspecting enabled rules

The parser exposes enabled rules as a dictionary.

```python
from wenmode import Parser
from wenmode.presets import commonmark

parser = Parser(commonmark)

if 'emphasis' in parser.rules:
    print('emphasis is enabled')
```

This is useful for rules that need to check whether another feature is enabled
without assuming a fixed preset.

For the syntax, generated node type, AST shape, and default HTML output of each
public rule, see [](reference.md).
