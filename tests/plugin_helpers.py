from __future__ import annotations

from collections.abc import Iterable

from wenmode import Wenmode
from wenmode.headings import HeadingIdTransform
from wenmode.nodes import Node
from wenmode.plugins import (
    abbr,
    block_math,
    block_spoiler,
    definition_list,
    fenced_directive,
    frontmatter,
    heading_ids,
    html_container,
    inline_math,
    inline_role,
    inline_spoiler,
    insert,
    mark,
    ruby,
    smartypants,
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
    'atx_heading_id': AtxHeading(transforms=[HeadingIdTransform()]),
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
    'heading_id_transform': AtxHeading(transforms=[HeadingIdTransform()]),
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

PLUGIN_RULES: dict[str, object] = {
    'abbreviation': abbr,
    'block_spoiler': block_spoiler,
    'definition_list': definition_list,
    'fenced_directive': fenced_directive,
    'frontmatter': frontmatter,
    'heading_ids': heading_ids,
    'html_container': html_container,
    'inline_math': inline_math,
    'inline_spoiler': inline_spoiler,
    'insert': insert,
    'mark': mark,
    'math_block': block_math,
    'role': inline_role,
    'ruby': ruby,
    'smartypants': smartypants,
    'smartypants_no_dashes': smartypants.configure(dashes=False),
    'subscript': subscript,
    'superscript': superscript,
}

PLUGIN_REGISTRY_TARGETS: list[object] = [
    abbr,
    definition_list,
    fenced_directive,
    frontmatter,
    heading_ids,
    html_container,
    inline_role,
    insert,
    mark,
    block_math,
    inline_math,
    ruby,
    block_spoiler,
    inline_spoiler,
    subscript,
    superscript,
]

PLUGIN_ROUND_TRIP_TARGETS: list[object] = [
    frontmatter,
    heading_ids,
    html_container,
    abbr,
    definition_list,
    fenced_directive,
    inline_role,
    insert,
    mark,
    block_math,
    inline_math,
    ruby,
    block_spoiler,
    inline_spoiler,
    subscript,
    superscript,
]


def collect_plugin_nodes(plugins: Iterable[object]) -> list[type[Node]]:
    nodes: list[type[Node]] = []
    for plugin in plugins:
        nodes.extend(getattr(plugin, 'nodes', []))
    return nodes


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

    installed_plugins: set[int] = set()
    for name in rule_names:
        plugin_spec = PLUGIN_RULES.get(name)
        if plugin_spec is not None:
            key = id(plugin_spec)
            if key not in installed_plugins:
                app.use(plugin_spec)
                installed_plugins.add(key)
            continue
        app.register_rule(STANDARD_RULES[name])
    return app
