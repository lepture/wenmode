from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from wenmode import Wenmode
from wenmode.plugins import (
    abbr,
    definition_list,
    fenced_directive,
    frontmatter,
    inline_role,
    insert,
    mark,
    math,
    ruby,
    spoiler,
    subscript,
    superscript,
)
from wenmode.renderers import BaseRenderer, DirectiveHtmlRenderer
from wenmode.rules import (
    AtxHeading,
    Autolink,
    BackslashEscape,
    Blockquote,
    CharacterReference,
    ContainerDirective,
    Emphasis,
    ExtendedAutolink,
    FencedCode,
    Footnote,
    FootnoteDefinition,
    HardBreak,
    HtmlBlock,
    Image,
    IndentedCode,
    InlineCode,
    LeafDirective,
    Link,
    List,
    RawHtml,
    ReferenceDefinition,
    Rule,
    SetextHeading,
    Strikethrough,
    Table,
    TextDirective,
    ThematicBreak,
)

RuleSpec = type[Rule] | Rule

STANDARD_RULES: dict[str, RuleSpec] = {
    'atx_heading': AtxHeading,
    'atx_heading_id': AtxHeading(id_transform=True),
    'autolink': Autolink,
    'backslash_escape': BackslashEscape,
    'blockquote': Blockquote,
    'character_reference': CharacterReference,
    'container_directive': ContainerDirective,
    'emphasis': Emphasis,
    'extended_autolink': ExtendedAutolink,
    'fenced_code': FencedCode,
    'footnote': Footnote,
    'footnote_definition': FootnoteDefinition,
    'hard_break': HardBreak,
    'heading_id_transform': AtxHeading(id_transform=True),
    'html_block': HtmlBlock,
    'html_block_disallow_iframe': HtmlBlock(disallowed_tags=['iframe']),
    'image': Image,
    'indented_code': IndentedCode,
    'inline_code': InlineCode,
    'leaf_directive': LeafDirective,
    'link': Link,
    'link_no_references': Link(references=False),
    'list': List,
    'raw_html': RawHtml,
    'reference_definition': ReferenceDefinition,
    'setext_heading': SetextHeading,
    'strikethrough': Strikethrough,
    'table': Table,
    'task_list': List(task=True),
    'text_directive': TextDirective,
    'thematic_break': ThematicBreak,
}

PluginSpec = tuple[Any, dict[str, object]]

PLUGIN_RULES: dict[str, PluginSpec] = {
    'abbreviation': (abbr, {}),
    'block_spoiler': (spoiler, {'inline': False}),
    'definition_list': (definition_list, {}),
    'fenced_directive': (fenced_directive, {}),
    'frontmatter': (frontmatter, {}),
    'inline_math': (math, {'block': False}),
    'inline_spoiler': (spoiler, {'block': False}),
    'insert': (insert, {}),
    'mark': (mark, {}),
    'math_block': (math, {'inline': False}),
    'role': (inline_role, {}),
    'ruby': (ruby, {}),
    'subscript': (subscript, {}),
    'superscript': (superscript, {}),
}


def configured_app(
    rule_names: Iterable[str] | None,
    renderer: BaseRenderer | None = None,
    directives: Iterable[DirectiveHtmlRenderer] = (),
    positions: bool = False,
) -> Wenmode:
    if rule_names is not None:
        rules = []
    else:
        rules = None
    app = Wenmode(rules, renderer=renderer, directives=directives, positions=positions)
    if rule_names is None:
        return app

    installed_plugins: set[tuple[int, tuple[tuple[str, object], ...]]] = set()
    for name in rule_names:
        plugin_spec = PLUGIN_RULES.get(name)
        if plugin_spec is not None:
            plugin, options = plugin_spec
            key = (id(plugin), tuple(sorted(options.items())))
            if key not in installed_plugins:
                app.use(plugin, **options)
                installed_plugins.add(key)
            continue
        app.register_rule(STANDARD_RULES[name])
    return app
