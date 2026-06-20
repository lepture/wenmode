(rules)=
# Rules

```{rst-class} lead
Understand how Wenmode composes Markdown syntax from opt-in parser rules.
```

---

Rules are opt-in and composable. A parser only recognizes syntax for rules that
you enable.

Read this page when you are building a custom dialect. If you only need common
Markdown, start with {ref}`presets`; if you need non-standard syntax packaged
with renderer behavior, start with {ref}`plugins`.

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
text = '# not a heading'

html = wenmode.render(text)
```

Pass classes or configured rule instances. Classes are instantiated
automatically, while instances let you choose rule options.

```python
from wenmode import Wenmode
from wenmode.rules import Image, Link

wenmode = Wenmode([
    Image(references=False),
    Link(references=False),
])
```

In this example, direct links and images are enabled, but reference-style links,
reference-style images, and reference definitions are not.

## Runtime registration

Rules can be registered after construction.

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading

wenmode = Wenmode([])
wenmode.register_rule(AtxHeading)
```

`register_rules()` accepts multiple rules:

```python
from wenmode import Wenmode
from wenmode.rules import AtxHeading, Emphasis, InlineCode

wenmode = Wenmode([])
wenmode.register_rules([AtxHeading, InlineCode, Emphasis])
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

If a feature needs both syntax and output behavior, register it through a plugin
so the rule and renderer handlers stay together.

## Rule order

Block and inline rules are sorted by their `order` value. When multiple inline
rules match at the same position, the sorted rule order decides which rule wins.

Most custom rules can keep the default order. Set a custom `order` only when
your rule must run before or after another syntax with overlapping markers.

Prefer changing rule order in the smallest possible rule set and cover the
overlap with tests. Rule order changes can affect unrelated syntax that shares
the same opening character.

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
public rule, see {ref}`Reference <reference>`.
