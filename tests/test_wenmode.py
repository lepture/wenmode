from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

import pytest

from wenmode import Parser, Wenmode
from wenmode.directives import Admonition
from wenmode.nodes import Literal, Parent
from wenmode.plugins import (
    BlockFenced,
    DeclarativePluginSpec,
    InlineLiteral,
    RendererFallback,
    RenderTemplate,
    inline_math,
    mark,
    plugin,
    ruby,
    smartypants,
)
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

    assert mark.nodes == mark.spec.nodes == [mark.MarkNode]
    assert mark.spec.syntax[0].opener == '=='
    assert wen.render('==marked *text*==\n') == '<p><mark>marked <em>text</em></mark></p>\n'
    assert wen.render('===not marked===\n') == '<p>===not marked===</p>\n'


def test_wenmode_installs_declarative_plugin_handlers() -> None:
    wen = Wenmode(plugins=[inline_math])

    assert not hasattr(inline_math, 'setup')
    assert inline_math.nodes == inline_math.spec.nodes == [inline_math.InlineMathNode]
    assert wen.render('$x < y$\n') == '<p><span class="math math-inline">x &lt; y</span></p>\n'


def test_wenmode_installs_declarative_inline_literal() -> None:
    class InlineLiteralPlugin:
        spec = DeclarativePluginSpec(
            name='custom_inline_literal',
            nodes=[CustomInlineLiteral],
            syntax=[
                InlineLiteral(
                    name='custom_inline_literal',
                    node=CustomInlineLiteral,
                    opener='$',
                    closer='$',
                    reject_adjacent_delimiter=True,
                    reject_closing_before_digit=True,
                )
            ],
            renderers={'html': {CustomInlineLiteral.type: RendererFallback('value')}},
        )

        nodes = spec.nodes

    wen = Wenmode(plugins=[InlineLiteralPlugin])

    assert wen.render('$value$ and $$not literal$$\n') == '<p>value and $$not literal$$</p>\n'
    assert wen.render('$value$5\n') == '<p>$value$5</p>\n'


def test_wenmode_installs_declarative_block_fenced_literal() -> None:
    class BlockLiteralPlugin:
        spec = DeclarativePluginSpec(
            name='custom_block_literal',
            nodes=[CustomBlockLiteral],
            syntax=[
                BlockFenced(
                    name='custom_block_literal',
                    node=CustomBlockLiteral,
                    opener='%%%',
                    closer='%%%',
                    strip_content=True,
                )
            ],
            renderers={'html': {CustomBlockLiteral.type: RenderTemplate('<aside>{value}</aside>\n')}},
        )

        nodes = spec.nodes

    wen = Wenmode(plugins=[BlockLiteralPlugin])

    assert wen.render('%%%\nbody\n%%%\n') == '<aside>body</aside>\n'


def test_wenmode_installs_declarative_block_fenced_children() -> None:
    class BlockParentPlugin:
        spec = DeclarativePluginSpec(
            name='custom_block_parent',
            nodes=[CustomBlockParent],
            syntax=[
                BlockFenced(
                    name='custom_block_parent',
                    node=CustomBlockParent,
                    opener='+++',
                    closer='+++',
                    content='children',
                )
            ],
            renderers={'html': {CustomBlockParent.type: RendererFallback('children')}},
        )

        nodes = spec.nodes

    wen = Wenmode(plugins=[BlockParentPlugin])

    assert wen.render('+++\n# Nested\n+++\n') == '<h1>Nested</h1>\n'


def test_wenmode_rejects_declarative_plugin_options() -> None:
    with pytest.raises(TypeError, match="declarative plugin 'mark' does not accept setup options: custom"):
        Wenmode().use(mark, custom=True)


def test_wenmode_uses_plugin_options() -> None:
    wen = Wenmode().use(smartypants, dashes=False)

    assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” -- ok</p>\n'


def test_wenmode_accepts_plugin_specs_during_initialization() -> None:
    wen = Wenmode([], plugins=[plugin(smartypants, dashes=False)])

    assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” -- ok</p>\n'


def test_wenmode_accepts_plugin_specs_with_use() -> None:
    wen = Wenmode([]).use(plugin(smartypants, dashes=False))

    assert wen.render('"Hello..." -- ok\n') == '<p>“Hello…” -- ok</p>\n'


def test_wenmode_rejects_plugin_spec_plus_extra_options() -> None:
    with pytest.raises(TypeError, match='plugin configs cannot be combined with extra options'):
        Wenmode([]).use(plugin(smartypants, dashes=False), quotes=False)


def test_wenmode_rejects_modules_without_setup() -> None:
    with pytest.raises(TypeError, match='plugins must define spec or setup'):
        Wenmode().use(ModuleType('empty_plugin'))


def test_wenmode_rejects_constructor_plugins_without_setup() -> None:
    with pytest.raises(TypeError, match='plugins must define spec or setup'):
        Wenmode(plugins=[ModuleType('empty_plugin')])


def test_wenmode_rejects_constructor_plugin_option_tuples() -> None:
    with pytest.raises(TypeError, match='plugins must define spec or setup'):
        Wenmode(plugins=[(smartypants, {'dashes': False})])


def test_wenmode_rejects_plugins_with_spec_and_setup() -> None:
    class AmbiguousPlugin:
        spec = DeclarativePluginSpec(name='ambiguous', nodes=[], syntax=[], renderers={})

        @staticmethod
        def setup(wen: Wenmode, **options: object) -> None:
            raise AssertionError('setup should not be called')

    with pytest.raises(TypeError, match='plugins must define either spec or setup, not both'):
        Wenmode().use(AmbiguousPlugin)


def test_wenmode_registers_renderer_handlers_for_current_renderer() -> None:
    wen = Wenmode([])

    def render_custom_literal(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<custom>{renderer.escape_html(node.value)}</custom>'

    def render_other(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return 'other'

    wen.register_renderer_handlers(
        {
            'html': {'customLiteral': render_custom_literal},
            'markdown': {'customLiteral': render_other},
        }
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
