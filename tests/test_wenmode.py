from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

import pytest

from tests.helpers import max_type_depth, text_values
from wenmode import Parser, Wenmode
from wenmode._declaratives import BlockFenced, InlineDelimited, InlineLiteral
from wenmode.directives import Admonition
from wenmode.nodes import Literal, Parent
from wenmode.plugins import inline_math, mark, ruby, smartypants
from wenmode.renderers import HTMLRenderer, RenderContext
from wenmode.rules import AtxHeading, ContainerDirective, Link


@dataclass
class CustomLiteral(Literal):
    type: str = 'customLiteral'


@dataclass
class CustomInlineLiteral(Literal):
    type: str = 'customInlineLiteral'


@dataclass
class CustomBlockLiteral(Literal):
    type: str = 'customBlockLiteral'


@dataclass
class CustomBlockParent(Parent):
    type: str = 'customBlockParent'


def test_wenmode_contains_parser_and_renderer() -> None:
    wen = Wenmode()

    assert isinstance(wen.parser, Parser)
    assert isinstance(wen.renderer, HTMLRenderer)
    assert wen.render('# Title\n') == '<h1>Title</h1>\n'


def test_wenmode_accepts_explicit_empty_rules() -> None:
    wen = Wenmode([])

    assert wen.render('# Title\n') == '<p># Title</p>\n'


def test_wenmode_registers_rules_dynamically() -> None:
    wen = Wenmode([Link])

    assert wen.render('# Title\n') == '<p># Title</p>\n'

    wen.register_rule(AtxHeading)

    assert wen.render('# Title\n') == '<h1>Title</h1>\n'


def test_wenmode_uses_plugins() -> None:
    wen = Wenmode([])

    assert wen.use(ruby) is wen
    assert wen.render('[漢字(kanji)]\n') == '<p><ruby>漢字<rt>kanji</rt></ruby></p>\n'


def test_wenmode_accepts_plugins_during_initialization() -> None:
    wen = Wenmode([], plugins=[ruby])

    assert wen.render('[漢字(kanji)]\n') == '<p><ruby>漢字<rt>kanji</rt></ruby></p>\n'


def test_wenmode_installs_declarative_plugin() -> None:
    wen = Wenmode(plugins=[mark])

    assert mark.nodes == [mark.MarkNode]
    assert mark.rules[0].pattern == '=='
    assert wen.render('==marked *text*==\n') == '<p><mark>marked <em>text</em></mark></p>\n'
    assert wen.render('===not marked===\n') == '<p>===not marked===</p>\n'


def test_wenmode_installs_declarative_plugin_handlers() -> None:
    wen = Wenmode(plugins=[inline_math])

    assert callable(inline_math.setup)
    assert inline_math.nodes == [inline_math.InlineMathNode]
    assert wen.render('$x < y$\n') == '<p><span class="math math-inline">x &lt; y</span></p>\n'


def test_wenmode_installs_declarative_inline_literal() -> None:
    class InlineLiteralPlugin:
        nodes = [CustomInlineLiteral]
        rules = [
            InlineLiteral(
                name='custom_inline_literal',
                node=CustomInlineLiteral,
                opener='$',
                closer='$',
                reject_adjacent_delimiter=True,
                reject_closing_before_digit=True,
            )
        ]
        handlers = {'html': {CustomInlineLiteral.type: lambda renderer, node, context: node.value}}

        @staticmethod
        def setup(wen: Wenmode, /) -> None:
            wen.register_rules(InlineLiteralPlugin.rules)
            wen.register_renderer_handlers(InlineLiteralPlugin.handlers)

    wen = Wenmode(plugins=[InlineLiteralPlugin])

    assert wen.render('$value$ and $$not literal$$\n') == '<p>value and $$not literal$$</p>\n'
    assert wen.render('$value$5\n') == '<p>$value$5</p>\n'


def test_wenmode_installs_declarative_literal_value() -> None:
    class DelimitedValuePlugin:
        nodes = [CustomInlineLiteral]
        rules = [
            InlineLiteral(
                name='custom_delimited_value',
                node=CustomInlineLiteral,
                opener='{%',
                closer='%}',
                reject_opening_whitespace=False,
                reject_closing_whitespace=False,
                reject_longer_run=False,
            )
        ]
        handlers = {'html': {CustomInlineLiteral.type: lambda renderer, node, context: f'<data>{node.value}</data>'}}

        @staticmethod
        def setup(wen: Wenmode, /) -> None:
            wen.register_rules(DelimitedValuePlugin.rules)
            wen.register_renderer_handlers(DelimitedValuePlugin.handlers)

    wen = Wenmode(plugins=[DelimitedValuePlugin])

    assert wen.render('A {% raw *value* %}.\n') == '<p>A <data> raw *value* </data>.</p>\n'


def test_wenmode_installs_declarative_delimited_children_with_asymmetric_delimiters() -> None:
    class DelimitedChildrenPlugin:
        nodes = [CustomBlockParent]
        rules = [
            InlineDelimited(
                name='custom_delimited_children',
                node=CustomBlockParent,
                opener='{+',
                closer='+}',
                reject_longer_run=False,
            )
        ]
        handlers = {
            'html': {
                CustomBlockParent.type: lambda renderer, node, context: (
                    f'<span>{renderer.render_children(node.children, context)}</span>'
                )
            }
        }

        @staticmethod
        def setup(wen: Wenmode, /) -> None:
            wen.register_rules(DelimitedChildrenPlugin.rules)
            wen.register_renderer_handlers(DelimitedChildrenPlugin.handlers)

    wen = Wenmode(plugins=[DelimitedChildrenPlugin])

    assert wen.render('A {+very *important*+} value.\n') == ('<p>A <span>very <em>important</em></span> value.</p>\n')


def test_wenmode_installs_declarative_block_fenced_literal() -> None:
    class BlockLiteralPlugin:
        nodes = [CustomBlockLiteral]
        rules = [
            BlockFenced(
                name='custom_block_literal', node=CustomBlockLiteral, opener='%%%', closer='%%%', strip_content=True
            )
        ]
        handlers = {'html': {CustomBlockLiteral.type: lambda renderer, node, context: f'<aside>{node.value}</aside>\n'}}

        @staticmethod
        def setup(wen: Wenmode, /) -> None:
            wen.register_rules(BlockLiteralPlugin.rules)
            wen.register_renderer_handlers(BlockLiteralPlugin.handlers)

    wen = Wenmode(plugins=[BlockLiteralPlugin])

    assert wen.render('%%%\nbody\n%%%\n') == '<aside>body</aside>\n'


def test_wenmode_installs_declarative_block_fenced_children() -> None:
    class BlockParentPlugin:
        nodes = [CustomBlockParent]
        rules = [
            BlockFenced(
                name='custom_block_parent', node=CustomBlockParent, opener='+++', closer='+++', content='children'
            )
        ]
        handlers = {
            'html': {
                CustomBlockParent.type: lambda renderer, node, context: renderer.render_children(node.children, context)
            }
        }

        @staticmethod
        def setup(wen: Wenmode, /) -> None:
            wen.register_rules(BlockParentPlugin.rules)
            wen.register_renderer_handlers(BlockParentPlugin.handlers)

    wen = Wenmode(plugins=[BlockParentPlugin])

    assert wen.render('+++\n# Nested\n+++\n') == '<h1>Nested</h1>\n'


def test_declarative_block_fenced_children_respects_max_container_depth() -> None:
    openers = ['+++', '===', '%%%', '$$$', '???', '!!!', '&&&', ';;;']

    class BlockParentPlugin:
        nodes = [CustomBlockParent]
        rules = [
            BlockFenced(
                name=f'custom_block_parent_{index}',
                node=CustomBlockParent,
                opener=opener,
                closer=f'/{opener}',
                content='children',
            )
            for index, opener in enumerate(openers)
        ]
        handlers = {
            'html': {
                CustomBlockParent.type: lambda renderer, node, context: renderer.render_children(node.children, context)
            }
        }

        @staticmethod
        def setup(wen: Wenmode, /) -> None:
            wen.register_rules(BlockParentPlugin.rules)
            wen.register_renderer_handlers(BlockParentPlugin.handlers)

    markdown = (
        ''.join(f'{opener}\n' for opener in openers)
        + 'deepest source\n'
        + ''.join(f'/{opener}\n' for opener in reversed(openers))
    )
    wen = Wenmode(plugins=[BlockParentPlugin])
    wen.parser.max_container_depth = 2

    ast = wen.parse(markdown).to_ast()

    assert max_type_depth(ast, CustomBlockParent.type) <= wen.parser.max_container_depth
    assert any('deepest source' in value for value in text_values(ast))


def test_wenmode_rejects_plugin_options() -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument 'custom'"):
        Wenmode().use(mark, custom=True)


def test_wenmode_uses_plugin_options() -> None:
    wen = Wenmode().use(smartypants.configure(dashes=False))

    assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” -- ok</p>\n'


def test_wenmode_accepts_plugin_specs_during_initialization() -> None:
    wen = Wenmode([], plugins=[smartypants.configure(dashes=False)])

    assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” -- ok</p>\n'


def test_wenmode_accepts_plugin_specs_with_use() -> None:
    wen = Wenmode([]).use(smartypants.configure(dashes=False))

    assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” -- ok</p>\n'


def test_wenmode_rejects_configured_plugin_plus_extra_options() -> None:
    with pytest.raises(TypeError, match="unexpected keyword argument 'quotes'"):
        Wenmode([]).use(smartypants.configure(dashes=False), quotes=False)


def test_wenmode_rejects_modules_without_setup() -> None:
    with pytest.raises(TypeError, match=r'plugins must define setup\(wen, /\)'):
        Wenmode().use(ModuleType('empty_plugin'))


def test_wenmode_rejects_constructor_plugins_without_setup() -> None:
    with pytest.raises(TypeError, match=r'plugins must define setup\(wen, /\)'):
        Wenmode(plugins=[ModuleType('empty_plugin')])


def test_wenmode_rejects_constructor_plugin_option_tuples() -> None:
    with pytest.raises(TypeError, match=r'plugins must define setup\(wen, /\)'):
        Wenmode(plugins=[(smartypants, {'dashes': False})])


def test_wenmode_uses_setup_even_when_plugin_exposes_metadata() -> None:
    class MetadataPlugin:
        name = 'metadata'
        nodes: list[type[Parent]] = []
        called = False

        @staticmethod
        def setup(wen: Wenmode, /) -> None:
            MetadataPlugin.called = True

    Wenmode().use(MetadataPlugin)

    assert MetadataPlugin.called is True


def test_wenmode_registers_renderer_handlers_for_current_renderer() -> None:
    wen = Wenmode([])

    def render_custom_literal(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<custom>{renderer.escape_html(node.value)}</custom>'

    def render_other(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return 'other'

    wen.register_renderer_handlers(
        {'html': {'customLiteral': render_custom_literal}, 'markdown': {'customLiteral': render_other}}
    )

    assert wen.render_node(CustomLiteral(value='<x>')) == '<custom>&lt;x&gt;</custom>'


def test_wenmode_renderer_handlers_are_instance_local() -> None:
    configured = Wenmode([])
    plain = Wenmode([])

    def render_custom_literal(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<custom>{renderer.escape_html(node.value)}</custom>'

    configured.register_renderer_handlers({'html': {'customLiteral': render_custom_literal}})

    assert configured.render_node(CustomLiteral(value='<x>')) == '<custom>&lt;x&gt;</custom>'
    assert plain.render_node(CustomLiteral(value='<x>')) == '&lt;x&gt;'


def test_wenmode_registers_directive_renderers_dynamically() -> None:
    wen = Wenmode([ContainerDirective])
    markdown = ':::note[Title]\nBody.\n:::\n'

    assert wen.render(markdown) == '<p>Title</p>\n<p>Body.</p>\n'

    wen.register_directive_renderer(Admonition())

    assert wen.render(markdown) == (
        '<aside class="admonition admonition-note">\n<p class="admonition-title">Title</p>\n<p>Body.</p>\n</aside>\n'
    )
