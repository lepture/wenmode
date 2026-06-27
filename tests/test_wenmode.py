from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

import pytest

from wenmode import Parser, Wenmode
from wenmode.directives import Admonition
from wenmode.nodes import Literal
from wenmode.plugins import math, plugin, ruby
from wenmode.renderers import HTMLRenderer, RenderContext
from wenmode.rules import AtxHeading, ContainerDirective, Link


@dataclass
class CustomLiteral(Literal):
    type: str = 'customLiteral'


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


def test_wenmode_uses_plugin_options() -> None:
    wen = Wenmode().use(math, inline=False)

    assert wen.render('Inline $x$.\n') == '<p>Inline $x$.</p>\n'
    assert wen.render('$$\nx\n$$\n') == '<div class="math math-display">x\n</div>\n'


def test_wenmode_accepts_plugin_specs_during_initialization() -> None:
    wen = Wenmode([], plugins=[plugin(math, inline=False)])

    assert wen.render('Inline $x$.\n') == '<p>Inline $x$.</p>\n'
    assert wen.render('$$\nx\n$$\n') == '<div class="math math-display">x\n</div>\n'


def test_wenmode_accepts_plugin_specs_with_use() -> None:
    wen = Wenmode([]).use(plugin(math, inline=False))

    assert wen.render('Inline $x$.\n') == '<p>Inline $x$.</p>\n'
    assert wen.render('$$\nx\n$$\n') == '<div class="math math-display">x\n</div>\n'


def test_wenmode_rejects_plugin_spec_plus_extra_options() -> None:
    with pytest.raises(TypeError, match='plugin specs cannot be combined with extra options'):
        Wenmode([]).use(plugin(math, inline=False), block=False)


def test_wenmode_rejects_modules_without_setup() -> None:
    with pytest.raises(TypeError, match='plugins must define setup'):
        Wenmode().use(ModuleType('empty_plugin'))


def test_wenmode_rejects_constructor_plugins_without_setup() -> None:
    with pytest.raises(TypeError, match='plugins must define setup'):
        Wenmode(plugins=[ModuleType('empty_plugin')])


def test_wenmode_rejects_constructor_plugin_option_tuples() -> None:
    with pytest.raises(TypeError, match='plugins must define setup'):
        Wenmode(plugins=[(math, {'inline': False})])


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
    assert plain.render_node(CustomLiteral(value='<x>')) == '<x>'


def test_wenmode_registers_directive_renderers_dynamically() -> None:
    wen = Wenmode([ContainerDirective])
    markdown = ':::note[Title]\nBody.\n:::\n'

    assert wen.render(markdown) == '<p>Title</p>\n<p>Body.</p>\n'

    wen.register_directive_renderer(Admonition())

    assert wen.render(markdown) == (
        '<aside class="admonition admonition-note">\n<p class="admonition-title">Title</p>\n<p>Body.</p>\n</aside>\n'
    )
