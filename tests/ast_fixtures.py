from __future__ import annotations

from typing import Any

from wenmode.nodes import (
    Blockquote,
    Break,
    Code,
    ContainerDirective,
    Delete,
    Emphasis,
    FootnoteDefinition,
    FootnoteReference,
    Heading,
    Html,
    Image,
    InlineCode,
    LeafDirective,
    Link,
    List,
    ListItem,
    LiteralDirective,
    Node,
    Paragraph,
    Root,
    Strong,
    Table,
    TableCell,
    TableRow,
    Text,
    TextDirective,
    ThematicBreak,
)
from wenmode.plugins import (
    abbr,
    definition_list,
    fenced_directive,
    frontmatter,
    html_container,
    inline_role,
    insert,
    mark,
    math,
    plugin,
    ruby,
    spoiler,
    subscript,
    superscript,
)

NodeShape = tuple[str, type[Node], dict[str, Any]]

TEXT_AST = {'type': 'text', 'value': 'text'}
INLINE_TEXT_AST = {'type': 'text', 'value': 'inline'}
PARAGRAPH_AST = {'type': 'paragraph', 'children': [TEXT_AST]}

BUILTIN_NODE_SHAPES: list[NodeShape] = [
    (
        'root',
        Root,
        {'type': 'root', 'children': [PARAGRAPH_AST]},
    ),
    (
        'paragraph',
        Paragraph,
        PARAGRAPH_AST,
    ),
    (
        'heading',
        Heading,
        {'type': 'heading', 'children': [TEXT_AST], 'depth': 2},
    ),
    (
        'blockquote',
        Blockquote,
        {'type': 'blockquote', 'children': [PARAGRAPH_AST]},
    ),
    (
        'list',
        List,
        {
            'type': 'list',
            'children': [
                {
                    'type': 'listItem',
                    'children': [PARAGRAPH_AST],
                    'checked': False,
                    'spread': True,
                }
            ],
            'ordered': True,
            'start': 3,
            'spread': True,
        },
    ),
    (
        'listItem',
        ListItem,
        {'type': 'listItem', 'children': [PARAGRAPH_AST], 'checked': True, 'spread': False},
    ),
    (
        'code',
        Code,
        {'type': 'code', 'value': 'print(1)\n', 'lang': 'python', 'meta': 'linenos'},
    ),
    (
        'thematicBreak',
        ThematicBreak,
        {'type': 'thematicBreak'},
    ),
    (
        'html',
        Html,
        {'type': 'html', 'data': {'escaped': True}, 'value': '&lt;script>alert(1)&lt;/script>\n'},
    ),
    (
        'text',
        Text,
        TEXT_AST,
    ),
    (
        'inlineCode',
        InlineCode,
        {'type': 'inlineCode', 'value': 'code'},
    ),
    (
        'strong',
        Strong,
        {'type': 'strong', 'children': [INLINE_TEXT_AST]},
    ),
    (
        'emphasis',
        Emphasis,
        {'type': 'emphasis', 'children': [INLINE_TEXT_AST]},
    ),
    (
        'delete',
        Delete,
        {'type': 'delete', 'children': [INLINE_TEXT_AST]},
    ),
    (
        'table',
        Table,
        {
            'type': 'table',
            'children': [
                {
                    'type': 'tableRow',
                    'children': [
                        {'type': 'tableCell', 'children': [TEXT_AST]},
                        {'type': 'tableCell', 'children': [INLINE_TEXT_AST]},
                    ],
                }
            ],
            'align': ['left', None],
        },
    ),
    (
        'tableRow',
        TableRow,
        {'type': 'tableRow', 'children': [{'type': 'tableCell', 'children': [TEXT_AST]}]},
    ),
    (
        'tableCell',
        TableCell,
        {'type': 'tableCell', 'children': [TEXT_AST]},
    ),
    (
        'link',
        Link,
        {'type': 'link', 'children': [TEXT_AST], 'url': '/url', 'title': 'Title'},
    ),
    (
        'image',
        Image,
        {'type': 'image', 'url': '/img.png', 'alt': 'Alt text', 'title': 'Title'},
    ),
    (
        'break',
        Break,
        {'type': 'break'},
    ),
    (
        'footnoteReference',
        FootnoteReference,
        {'type': 'footnoteReference', 'identifier': 'note-id', 'label': 'Note Label'},
    ),
    (
        'footnoteDefinition',
        FootnoteDefinition,
        {'type': 'footnoteDefinition', 'children': [PARAGRAPH_AST], 'identifier': 'note-id', 'label': 'Note Label'},
    ),
    (
        'textDirective',
        TextDirective,
        {'type': 'textDirective', 'children': [TEXT_AST], 'name': 'abbr', 'attributes': {'title': 'Full name'}},
    ),
    (
        'leafDirective',
        LeafDirective,
        {'type': 'leafDirective', 'children': [TEXT_AST], 'name': 'youtube', 'attributes': {'id': 'abc'}},
    ),
    (
        'containerDirective',
        ContainerDirective,
        {'type': 'containerDirective', 'children': [PARAGRAPH_AST], 'name': 'note', 'attributes': {'class': 'wide'}},
    ),
    (
        'literalDirective',
        LiteralDirective,
        {
            'type': 'literalDirective',
            'value': 'print("*literal*")\n',
            'name': 'code-block',
            'argument': 'python',
            'attributes': {'caption': 'example.py'},
        },
    ),
]

PLUGIN_NODE_SAMPLES: list[NodeShape] = [
    (
        'abbreviation',
        abbr.AbbreviationNode,
        {'type': 'abbreviation', 'children': [TEXT_AST], 'title': 'HyperText Markup Language'},
    ),
    (
        'definitionList',
        definition_list.DefinitionListNode,
        {
            'type': 'definitionList',
            'children': [
                {'type': 'definitionTerm', 'children': [TEXT_AST]},
                {
                    'type': 'definitionDescription',
                    'children': [PARAGRAPH_AST],
                    'spread': False,
                },
            ],
        },
    ),
    (
        'definitionTerm',
        definition_list.DefinitionTermNode,
        {'type': 'definitionTerm', 'children': [TEXT_AST]},
    ),
    (
        'definitionDescription',
        definition_list.DefinitionDescriptionNode,
        {'type': 'definitionDescription', 'children': [PARAGRAPH_AST], 'spread': True},
    ),
    (
        'htmlContainer',
        html_container.HtmlContainerNode,
        {
            'type': 'htmlContainer',
            'data': {'escaped': True},
            'children': [PARAGRAPH_AST],
            'name': 'div',
            'attributes': {'id': 'steps', 'hidden': True},
            'opening': '<div id="steps" hidden>',
            'closing': '</div>',
        },
    ),
    (
        'math',
        math.MathNode,
        {'type': 'math', 'value': 'x + y\n'},
    ),
    (
        'inlineMath',
        math.InlineMathNode,
        {'type': 'inlineMath', 'value': 'x + y'},
    ),
    (
        'blockSpoiler',
        spoiler.BlockSpoilerNode,
        {'type': 'blockSpoiler', 'children': [PARAGRAPH_AST]},
    ),
    (
        'inlineSpoiler',
        spoiler.InlineSpoilerNode,
        {'type': 'inlineSpoiler', 'children': [TEXT_AST]},
    ),
    (
        'mark',
        mark.MarkNode,
        {'type': 'mark', 'children': [TEXT_AST]},
    ),
    (
        'insert',
        insert.InsertNode,
        {'type': 'insert', 'children': [TEXT_AST]},
    ),
    (
        'superscript',
        superscript.SuperscriptNode,
        {'type': 'superscript', 'children': [TEXT_AST]},
    ),
    (
        'subscript',
        subscript.SubscriptNode,
        {'type': 'subscript', 'children': [TEXT_AST]},
    ),
    (
        'ruby',
        ruby.RubyNode,
        {'type': 'ruby', 'segments': [{'base': '漢字', 'text': 'kanji'}]},
    ),
]

PLUGIN_REGISTRY_TARGETS: list[object] = [
    abbr,
    definition_list,
    fenced_directive,
    frontmatter,
    html_container,
    inline_role,
    insert,
    mark,
    plugin(math, inline=False),
    ruby,
    spoiler,
    subscript,
    superscript,
]

PLUGIN_ROUND_TRIP_TARGETS: list[object] = [
    frontmatter,
    html_container,
    abbr,
    definition_list,
    fenced_directive,
    inline_role,
    insert,
    mark,
    math,
    ruby,
    spoiler,
    subscript,
    superscript,
]

PLUGIN_ROUND_TRIP_MARKDOWN = '''---
title: AST contract
---

The HTML spec uses ==mark==, ^^insert^^, H~2~O, 2^10^, [漢字(kanji)], >! secret !<,
$x + y$, and {abbr}`CPU`.

*[HTML]: HyperText Markup Language

Apple
: *fruit*

>! hidden *thing*

<div id="steps" hidden>
- one
</div>

$$
x + y
$$

```{code-block} python
print("*literal*")
```
'''

PLUGIN_ROUND_TRIP_NODE_TYPES = {
    'root',
    'abbreviation',
    'definitionList',
    'definitionTerm',
    'definitionDescription',
    'htmlContainer',
    'mark',
    'insert',
    'subscript',
    'superscript',
    'ruby',
    'inlineSpoiler',
    'blockSpoiler',
    'inlineMath',
    'math',
    'textDirective',
    'literalDirective',
}
