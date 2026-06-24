from __future__ import annotations

from typing import Any, TypedDict

import pytest

from tests.helpers import load_fixture
from tests.plugin_helpers import configured_app
from wenmode import HTMLRenderer, MarkdownRenderer, RSTRenderer, Wenmode
from wenmode.directives import Abbreviation, Admonition, Details, Figure, TableOfContents
from wenmode.plugins import fenced_directive
from wenmode.rules import (
    AtxHeading,
    ContainerDirective,
    Emphasis,
    LeafDirective,
    TextDirective,
)
from wenmode.rules import Image as ImageRule


class DirectiveExample(TypedDict):
    name: str
    markdown: str
    ast: dict[str, Any]


class DirectiveHtmlExampleBase(TypedDict):
    name: str
    markdown: str
    html: str


class DirectiveHtmlExample(DirectiveHtmlExampleBase, total=False):
    admonition_names: list[str]


@pytest.mark.parametrize(
    'example',
    load_fixture('directives_ast.json'),
    ids=lambda example: example['name'],
)
def test_directive_ast_examples(example: DirectiveExample) -> None:
    app = configured_app(
        ['text_directive', 'role', 'leaf_directive', 'container_directive', 'fenced_directive', 'emphasis']
    )

    assert app.parse(example['markdown']).to_ast() == example['ast']


@pytest.mark.parametrize(
    'example',
    load_fixture('directives_html.json'),
    ids=lambda example: example['name'],
)
def test_directive_html_examples(example: DirectiveHtmlExample) -> None:
    admonition_names = example.get('admonition_names')
    if admonition_names is not None:
        admonition = Admonition(names=admonition_names)
    else:
        admonition = Admonition()
    app = Wenmode(
        [ContainerDirective, TextDirective, ImageRule],
        renderer=HTMLRenderer(directives=[admonition, Details(), Figure()]),
    )

    assert app.render(example['markdown']) == example['html']


def test_directives_are_plain_text_without_rules() -> None:
    markdown = ':abbr[HTML]{title="HyperText Markup Language"}\n\n{term}`HTML`\n\n::youtube[Video]{#abc}\n'

    assert Wenmode([]).render(markdown) == (
        '<p>:abbr[HTML]{title=&quot;HyperText Markup Language&quot;}</p>\n'
        '<p>{term}`HTML`</p>\n'
        '<p>::youtube[Video]{#abc}</p>\n'
    )


def test_html_renderer_falls_back_to_directive_children() -> None:
    app = Wenmode([TextDirective, LeafDirective, ContainerDirective])

    assert app.render(':i[inline]\n\n::hr[leaf]\n\n:::note[Title]\nBody.\n:::\n') == (
        '<p>inline</p>\nleaf<p>Title</p>\n<p>Body.</p>\n'
    )


def test_abbreviation_directive_renders_html() -> None:
    app = Wenmode([TextDirective, Emphasis], directives=[Abbreviation()])

    assert app.render(':abbr[*HTML*]{title="HyperText Markup Language" .term}\n') == (
        '<p><abbr title="HyperText Markup Language" class="term"><em>HTML</em></abbr></p>\n'
    )


def test_abbreviation_directive_falls_back_without_title() -> None:
    app = configured_app(['text_directive', 'role'], directives=[Abbreviation()])

    assert app.render(':abbr[HTML]\n') == '<p>HTML</p>\n'


def test_builtin_directives_drop_event_and_style_attributes() -> None:
    app = Wenmode([ContainerDirective], renderer=HTMLRenderer(directives=[Figure()]))

    assert app.render(':::figure{#fig .wide onclick="alert(1)" style="position:fixed" empty}\n:::\n') == (
        '<figure id="fig" empty="" class="wide">\n</figure>\n'
    )


def test_html_renderer_can_disable_attribute_sanitization() -> None:
    app = Wenmode([ContainerDirective], renderer=HTMLRenderer(sanitize_attrs=False, directives=[Figure()]))

    assert app.render(':::figure{onclick="alert(1)"}\n:::\n') == ('<figure onclick="alert(1)">\n</figure>\n')


def test_markdown_renderer_outputs_directives() -> None:
    app = configured_app(
        ['text_directive', 'role', 'leaf_directive', 'container_directive'],
        renderer=MarkdownRenderer(),
    )
    markdown = ':i[inline]{.x} and {role}`text`\n\n::hr[leaf]{flag}\n\n:::note[Title]{#n}\nBody.\n:::\n'

    assert app.render(markdown) == (
        ':i[inline]{.x} and :role[text]\n\n::hr[leaf]{flag}\n\n:::note[Title]{#n}\nBody\\.\n:::\n'
    )


def test_fenced_directive_serializes_as_container_directive() -> None:
    app = configured_app(['fenced_directive'], renderer=MarkdownRenderer())
    markdown = '```{note} Important\n:class: warning\n\nBody.\n```\n'

    assert app.render(markdown) == ':::note[Important]{.warning}\nBody\\.\n:::\n'


def test_fenced_code_stays_code_when_not_directive() -> None:
    assert configured_app(['fenced_directive', 'fenced_code']).render('```py\nprint(1)\n```\n') == (
        '<pre><code class="language-py">print(1)\n</code></pre>\n'
    )


def test_fenced_directive_order_is_before_fenced_code() -> None:
    app = configured_app(['fenced_code', 'fenced_directive'], renderer=MarkdownRenderer())

    assert app.render('```{note} Important\nBody.\n```\n') == (':::note[Important]\nBody\\.\n:::\n')


def test_fenced_literal_directive_preserves_code_block_body() -> None:
    markdown = '```{code-block} python\n:caption: example.py\n\nprint("*not emphasis*")\n```\n'
    app = configured_app(['fenced_directive', 'emphasis'])
    root = app.parse(markdown)

    assert root.to_ast() == {
        'type': 'root',
        'children': [
            {
                'type': 'literalDirective',
                'value': 'print("*not emphasis*")\n',
                'name': 'code-block',
                'argument': 'python',
                'attributes': {'caption': 'example.py'},
            }
        ],
    }
    assert app.render_node(root) == '<pre><code class="language-python">print(&quot;*not emphasis*&quot;)\n</code></pre>\n'


def test_literal_directive_renderers_preserve_fenced_and_rst_forms() -> None:
    markdown = '```{code-block} python\n:caption: example.py\n\nprint("*not emphasis*")\n```\n'

    assert configured_app(['fenced_directive'], renderer=MarkdownRenderer()).render(markdown) == markdown
    assert configured_app(['fenced_directive'], renderer=RSTRenderer()).render(markdown) == (
        '.. code-block:: python\n'
        '   :caption: example.py\n'
        '\n'
        '   print("*not emphasis*")\n'
    )


def test_fenced_directive_literal_names_are_configurable() -> None:
    app = Wenmode([]).use(fenced_directive, literal_names=())

    assert app.parse('```{code-block} python\n*body*\n```\n').to_ast() == {
        'type': 'root',
        'children': [
            {
                'type': 'containerDirective',
                'children': [
                    {
                        'type': 'paragraph',
                        'data': {'directiveLabel': True},
                        'children': [{'type': 'text', 'value': 'python'}],
                    },
                    {'type': 'paragraph', 'children': [{'type': 'text', 'value': '*body*'}]},
                ],
                'name': 'code-block',
            }
        ],
    }


def test_fenced_directive_fence_chars_are_configurable() -> None:
    default_app = Wenmode([]).use(fenced_directive)
    custom_app = Wenmode([], renderer=RSTRenderer()).use(
        fenced_directive,
        literal_names={'sourcecode'},
        fence=('`', '~', ':'),
    )

    assert default_app.render(':::{note} Title\nBody.\n:::\n') == '<p>:::{note} Title\nBody.\n:::</p>\n'
    assert custom_app.render(':::{note} Title\nBody.\n:::\n') == '.. note:: Title\n\n   Body.\n'
    assert custom_app.render(':::{sourcecode} python\nvalue = node.value[start:end]\n:::\n') == (
        '.. sourcecode:: python\n\n   value = node.value[start:end]\n'
    )


def test_fenced_directive_rejects_invalid_fence_config() -> None:
    with pytest.raises(ValueError, match='at least one character'):
        Wenmode([]).use(fenced_directive, fence=())

    with pytest.raises(ValueError, match='single characters'):
        Wenmode([]).use(fenced_directive, fence=('::',))


def test_fenced_directive_handles_empty_and_unclosed_bodies() -> None:
    app = Wenmode([], renderer=RSTRenderer()).use(fenced_directive)

    assert app.render('```{note}\n```\n') == '.. note::\n'
    assert app.render('```{note}') == '.. note::\n'
    assert app.render('```{code-block} python\n') == '.. code-block:: python\n'
    assert app.render('```{note}\n:class: warning\n') == '.. note::\n   :class: warning\n'
    assert app.render('```{note}\nBody without closer.\n') == '.. note::\n\n   Body without closer.\n'


def test_toc_leaf_directive_renders_heading_links() -> None:
    app = Wenmode(
        [AtxHeading(id_transform=True), LeafDirective, ContainerDirective, Emphasis],
        directives=[TableOfContents()],
    )

    assert app.render(
        '::toc[On this page]{min=2 max=3 .wide}\n\n# Title\n\n## Usage *Guide*\n\n### Install\n\n## Usage Guide\n'
    ) == (
        '<nav class="wide toc" aria-label="On this page">\n'
        '<ol>\n'
        '<li><a href="#usage-guide">Usage Guide</a>\n'
        '<ol>\n'
        '<li><a href="#install">Install</a></li>\n'
        '</ol>\n'
        '</li>\n'
        '<li><a href="#usage-guide-1">Usage Guide</a></li>\n'
        '</ol>\n'
        '</nav>\n'
        '<h1 id="title">Title</h1>\n'
        '<h2 id="usage-guide">Usage <em>Guide</em></h2>\n'
        '<h3 id="install">Install</h3>\n'
        '<h2 id="usage-guide-1">Usage Guide</h2>\n'
    )


def test_toc_directive_uses_existing_heading_ids_even_when_rendered_late() -> None:
    app = Wenmode([AtxHeading(id_transform=True), LeafDirective], directives=[TableOfContents()])

    assert app.render('## Before\n\n::toc{min-depth=2 max-depth=2 id=contents label=Contents}\n') == (
        '<h2 id="before">Before</h2>\n'
        '<nav id="contents" aria-label="Contents" class="toc">\n'
        '<ol>\n'
        '<li><a href="#before">Before</a></li>\n'
        '</ol>\n'
        '</nav>\n'
    )


def test_toc_directive_does_not_create_heading_ids() -> None:
    app = Wenmode([AtxHeading, LeafDirective], directives=[TableOfContents()])

    assert app.render('## Before\n\n::toc{min=2 max=2}\n') == '<h2>Before</h2>\n'
