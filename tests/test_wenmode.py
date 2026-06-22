from __future__ import annotations

from dataclasses import dataclass
from types import ModuleType

import pytest

from wenmode import Parser, Wenmode
from wenmode.directives import Admonition
from wenmode.nodes import Literal
from wenmode.plugins import ruby
from wenmode.renderers import HTMLRenderer, RenderContext
from wenmode.rules import AtxHeading, ContainerDirective, Link


@dataclass
class CustomLiteral(Literal):
    type: str = 'customLiteral'


def test_wenmode_contains_parser_and_renderer() -> None:
    wenmode = Wenmode()

    assert isinstance(wenmode.parser, Parser)
    assert isinstance(wenmode.renderer, HTMLRenderer)
    assert wenmode.render('# Title\n') == '<h1>Title</h1>\n'


def test_wenmode_accepts_explicit_empty_rules() -> None:
    wenmode = Wenmode([])

    assert wenmode.render('# Title\n') == '<p># Title</p>\n'


def test_wenmode_registers_rules_dynamically() -> None:
    wenmode = Wenmode([Link])

    assert wenmode.render('# Title\n') == '<p># Title</p>\n'

    wenmode.register_rule(AtxHeading)

    assert wenmode.render('# Title\n') == '<h1>Title</h1>\n'


def test_wenmode_uses_plugins() -> None:
    wenmode = Wenmode([])

    assert wenmode.use(ruby) is wenmode
    assert wenmode.render('[漢字(kanji)]\n') == '<p><ruby>漢字<rt>kanji</rt></ruby></p>\n'


def test_wenmode_rejects_modules_without_setup() -> None:
    with pytest.raises(TypeError, match='plugins must define setup'):
        Wenmode().use(ModuleType('empty_plugin'))


def test_wenmode_registers_renderer_handlers_for_current_renderer() -> None:
    wenmode = Wenmode([])

    def render_custom_literal(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<custom>{renderer.escape_html(node.value)}</custom>'

    def render_other(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return 'other'

    wenmode.register_renderer_handlers(
        {
            'html': {'customLiteral': render_custom_literal},
            'markdown': {'customLiteral': render_other},
        }
    )

    assert wenmode.render_node(CustomLiteral(value='<x>')) == '<custom>&lt;x&gt;</custom>'


def test_wenmode_renderer_handlers_are_instance_local() -> None:
    configured = Wenmode([])
    plain = Wenmode([])

    def render_custom_literal(renderer: HTMLRenderer, node: CustomLiteral, context: RenderContext) -> str:
        return f'<custom>{renderer.escape_html(node.value)}</custom>'

    configured.register_renderer_handlers({'html': {'customLiteral': render_custom_literal}})

    assert configured.render_node(CustomLiteral(value='<x>')) == '<custom>&lt;x&gt;</custom>'
    assert plain.render_node(CustomLiteral(value='<x>')) == '<x>'


def test_wenmode_registers_directive_renderers_dynamically() -> None:
    wenmode = Wenmode([ContainerDirective])
    markdown = ':::note[Title]\nBody.\n:::\n'

    assert wenmode.render(markdown) == '<p>Title</p>\n<p>Body.</p>\n'

    wenmode.register_directive_renderer(Admonition())

    assert wenmode.render(markdown) == (
        '<aside class="admonition admonition-note">\n<p class="admonition-title">Title</p>\n<p>Body.</p>\n</aside>\n'
    )
