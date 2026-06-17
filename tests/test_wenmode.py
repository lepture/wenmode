from __future__ import annotations

from wenmode import Parser, Wenmode
from wenmode.directives import Admonition
from wenmode.renderers import HTMLRenderer
from wenmode.rules import AtxHeading, ContainerDirective, Link


def render(wenmode: Wenmode, markdown: str) -> str:
    return wenmode.render(wenmode.parse(markdown))


def test_wenmode_contains_parser_and_renderer() -> None:
    wenmode = Wenmode()

    assert isinstance(wenmode.parser, Parser)
    assert isinstance(wenmode.renderer, HTMLRenderer)
    assert render(wenmode, '# Title\n') == '<h1>Title</h1>\n'


def test_wenmode_accepts_explicit_empty_rules() -> None:
    wenmode = Wenmode([])

    assert render(wenmode, '# Title\n') == '<p># Title</p>\n'


def test_wenmode_registers_rules_dynamically() -> None:
    wenmode = Wenmode([Link])

    assert render(wenmode, '# Title\n') == '<p># Title</p>\n'

    wenmode.register_rule(AtxHeading)

    assert render(wenmode, '# Title\n') == '<h1>Title</h1>\n'


def test_wenmode_registers_directive_renderers_dynamically() -> None:
    wenmode = Wenmode([ContainerDirective])
    markdown = ':::note[Title]\nBody.\n:::\n'

    assert render(wenmode, markdown) == '<p>Title</p>\n<p>Body.</p>\n'

    wenmode.register_directive_renderer(Admonition())

    assert render(wenmode, markdown) == (
        '<aside class="admonition admonition-note">\n'
        '<p class="admonition-title">Title</p>\n'
        '<p>Body.</p>\n'
        '</aside>\n'
    )
