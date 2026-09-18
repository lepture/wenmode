from __future__ import annotations

import pytest

from wenmode import HTMLRenderer, Parser, Wenmode
from wenmode.ast import plain_text
from wenmode.directives import Figure, TableOfContents
from wenmode.headings import GENERATED_HEADING_IDS, HeadingIdTransform, Slugger, add_heading_ids
from wenmode.nodes import ContainerDirective as ContainerDirectiveNode
from wenmode.nodes import Heading, Node, Root, Text
from wenmode.plugins import heading_ids
from wenmode.rules import AtxHeading, ContainerDirective, LeafDirective, NodeTransform, RootTransform, SetextHeading
from wenmode.state import BlockState
from wenmode.toc import render_toc_html


def test_heading_id_transform_adds_heading_ids() -> None:
    app = Wenmode([AtxHeading(transforms=[HeadingIdTransform()])])

    assert app.render('## Intro\n\n## Intro\n') == '<h2 id="intro">Intro</h2>\n<h2 id="intro-1">Intro</h2>\n'


def test_heading_id_transform_dedupes_atx_and_setext_headings() -> None:
    transform = HeadingIdTransform()
    app = Wenmode([AtxHeading(transforms=[transform]), SetextHeading(transforms=[transform])])

    assert app.render('# Intro\n\nIntro\n-----\n') == '<h1 id="intro">Intro</h1>\n<h2 id="intro-1">Intro</h2>\n'


def test_heading_ids_do_not_collide_with_existing_numbered_title() -> None:
    app = Wenmode(plugins=[heading_ids])

    assert app.render('# Alpha\n\n# Alpha-1\n\n# Alpha\n') == (
        '<h1 id="alpha">Alpha</h1>\n<h1 id="alpha-1">Alpha-1</h1>\n<h1 id="alpha-2">Alpha</h1>\n'
    )


def test_heading_ids_do_not_reuse_generated_suffix_as_new_base() -> None:
    app = Wenmode(plugins=[heading_ids])

    assert app.render('# Alpha\n\n# Alpha\n\n# Alpha-1\n') == (
        '<h1 id="alpha">Alpha</h1>\n<h1 id="alpha-1">Alpha</h1>\n<h1 id="alpha-1-1">Alpha-1</h1>\n'
    )


def test_slugger_skips_reserved_suffixes() -> None:
    slugger = Slugger()
    slugger.use('alpha-1')
    slugger.use('alpha-2')

    assert slugger.slug('Alpha') == 'alpha'
    assert slugger.slug('Alpha') == 'alpha-3'
    assert slugger.slug('Alpha') == 'alpha-4'


def test_slugger_reserving_an_id_is_idempotent() -> None:
    slugger = Slugger()
    slugger.use('alpha')
    slugger.use('alpha')

    assert slugger.slug('Alpha') == 'alpha-1'


@pytest.mark.parametrize('before', [True, False])
def test_generated_heading_ids_avoid_explicit_directive_ids(before: bool) -> None:
    app = Wenmode([AtxHeading, ContainerDirective], plugins=[heading_ids], directives=[Figure()])
    figure = ':::figure{#alpha}\nbody\n:::\n\n'
    heading = '# Alpha\n\n'
    markdown = figure + heading if before else heading + figure

    html = app.render(markdown)

    assert '<figure id="alpha">' in html
    assert '<h1 id="alpha-1">Alpha</h1>' in html
    assert app.render(iter(markdown.splitlines(keepends=True))) == html


def test_toc_links_use_ids_after_explicit_directive_collision_is_resolved() -> None:
    app = Wenmode([AtxHeading, LeafDirective], plugins=[heading_ids], directives=[TableOfContents()])

    html = app.render('# Alpha\n\n::toc{#alpha}\n')

    assert '<h1 id="alpha-1">Alpha</h1>' in html
    assert '<a href="#alpha-1">Alpha</a>' in html
    assert '<nav id="alpha"' in html


@pytest.mark.parametrize('attribute', ['id="alpha"', "ID='al&#112;ha'", 'id=alpha'])
def test_generated_heading_ids_avoid_later_raw_html_ids(attribute: str) -> None:
    app = Wenmode(plugins=[heading_ids], renderer=HTMLRenderer(escape=False))

    html = app.render('# Alpha\n\n<div ' + attribute + '>body</div>\n')

    assert '<h1 id="alpha-1">Alpha</h1>' in html


def test_malformed_html_declarations_do_not_hide_later_ids_or_break_parsing() -> None:
    app = Wenmode(plugins=[heading_ids], renderer=HTMLRenderer(escape=False))

    html = app.render('# Alpha\n\n<div>\n<![unknown]>\n<span id="alpha">body</span>\n</div>\n')

    assert '<h1 id="alpha-1">Alpha</h1>' in html


class ExplicitHeadingId(NodeTransform):
    name = 'explicit_heading_id'

    def transform(self, parser: Parser, node: Node, state: BlockState) -> None:
        if plain_text(node) == 'Reserved':
            node.data = {'id': 'alpha'}


def test_generated_heading_ids_avoid_later_explicit_heading_ids() -> None:
    app = Wenmode([AtxHeading(transforms=[HeadingIdTransform(), ExplicitHeadingId()])])

    assert app.render('# Alpha\n\n# Reserved\n') == (
        '<h1 id="alpha-1">Alpha</h1>\n<h1 id="alpha">Reserved</h1>\n'
    )


class ExplicitRootHeadingId(RootTransform):
    name = 'explicit_root_heading_id'

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        root.children[-1].data = {'id': 'alpha'}


def test_heading_id_collisions_are_resolved_after_root_transforms() -> None:
    rule = AtxHeading(transforms=[HeadingIdTransform()])
    rule.root_transforms.append(ExplicitRootHeadingId())

    assert Wenmode([rule]).render('# Alpha\n\n# Reserved\n') == (
        '<h1 id="alpha-1">Alpha</h1>\n<h1 id="alpha">Reserved</h1>\n'
    )


def test_add_heading_ids_reserves_explicit_ids_before_generating_any_ids() -> None:
    first = Heading(depth=1, children=[Text(value='Alpha')])
    explicit = Heading(depth=2, children=[Text(value='Reserved')], data={'id': 'alpha'})
    directive = ContainerDirectiveNode(name='figure', attributes={'id': 'alpha-1'})
    root = Root(children=[first, explicit, directive])

    add_heading_ids(root, slugger=Slugger(), max_depth=1)

    assert first.data == {'id': 'alpha-2'}
    assert explicit.data == {'id': 'alpha'}


def test_add_heading_ids_can_reuse_ids_it_overwrites() -> None:
    heading = Heading(depth=1, children=[Text(value='Alpha')], data={'id': 'alpha'})

    add_heading_ids(heading, slugger=Slugger(), overwrite=True)

    assert heading.data == {'id': 'alpha'}


class PrefixedSlugger(Slugger):
    name = 'prefixed'

    def slug(self, value: str) -> str:
        return 'section-' + super().slug(value)


def test_explicit_ids_are_checked_against_custom_slugger_final_output() -> None:
    app = Wenmode(
        [AtxHeading, ContainerDirective],
        plugins=[heading_ids.configure(PrefixedSlugger)],
        directives=[Figure()],
    )

    html = app.render('# Alpha\n\n:::figure{#section-alpha}\n:::\n')

    assert '<h1 id="section-alpha-1">Alpha</h1>' in html


class ConstantSlugger(Slugger):
    name = 'constant'

    def slug(self, value: str) -> str:
        return 'fixed'


def test_collision_resolution_does_not_loop_with_constant_custom_slugger() -> None:
    app = Wenmode(
        [AtxHeading, ContainerDirective], plugins=[heading_ids.configure(ConstantSlugger)], directives=[Figure()]
    )

    html = app.render('# Alpha\n\n# Beta\n\n:::figure{#fixed}\n:::\n')

    assert '<h1 id="fixed-1">Alpha</h1>' in html
    assert '<h1 id="fixed-2">Beta</h1>' in html


class FinalizeProbe(NodeTransform):
    name = 'finalize_probe'

    def __init__(self) -> None:
        self.calls: list[str] = []

    def transform(self, parser: Parser, node: Node, state: BlockState) -> None:
        self.calls.append('node')

    def finalize(self, parser: Parser, root: Root, state: BlockState) -> None:
        self.calls.append('finalize')


def test_node_transform_finalizes_once_after_all_owning_rules() -> None:
    transform = FinalizeProbe()
    app = Wenmode([AtxHeading(transforms=[transform]), SetextHeading(transforms=[transform])])

    app.parse('# First\n\nSecond\n------\n')

    assert transform.calls == ['node', 'node', 'finalize']


def test_incremental_parse_does_not_finalize_node_transforms() -> None:
    transform = FinalizeProbe()
    parser = Parser([AtxHeading(transforms=[transform])])

    assert len(list(parser.parse_iter('# First\n# Second\n'))) == 2
    assert transform.calls == ['node', 'node']


def test_incremental_heading_ids_do_not_retain_nodes_for_batch_finalization() -> None:
    class StateProbe(NodeTransform):
        name = 'state_probe'
        state: BlockState | None = None

        def transform(self, parser: Parser, node: Node, state: BlockState) -> None:
            self.state = state

    probe = StateProbe()
    parser = Parser([AtxHeading(transforms=[HeadingIdTransform(), probe])])
    for _ in parser.parse_iter('# Title\n' * 100):
        assert probe.state is not None
        assert probe.state.store.get(GENERATED_HEADING_IDS) == {}


def test_heading_id_transform_uses_fresh_slugger_per_parse() -> None:
    app = Wenmode([AtxHeading(transforms=[HeadingIdTransform()])])

    assert app.render('## Intro\n') == '<h2 id="intro">Intro</h2>\n'
    assert app.render('## Intro\n') == '<h2 id="intro">Intro</h2>\n'


def test_heading_ids_plugin_adds_ids_to_enabled_heading_rules() -> None:
    app = Wenmode([AtxHeading, SetextHeading], plugins=[heading_ids])

    assert app.render('# Intro\n\nIntro\n-----\n') == '<h1 id="intro">Intro</h1>\n<h2 id="intro-1">Intro</h2>\n'


def test_heading_ids_plugin_does_not_enable_missing_heading_rules() -> None:
    app = Wenmode([AtxHeading], plugins=[heading_ids])

    assert app.render('# Intro\n\nIntro\n-----\n') == '<h1 id="intro">Intro</h1>\n<p>Intro\n-----</p>\n'


def test_heading_ids_plugin_does_not_duplicate_existing_transform() -> None:
    app = Wenmode([AtxHeading(transforms=[HeadingIdTransform()])], plugins=[heading_ids])

    assert app.render('# Intro\n\n# Intro\n') == '<h1 id="intro">Intro</h1>\n<h1 id="intro-1">Intro</h1>\n'


def test_render_empty_toc_html() -> None:
    assert render_toc_html([]) == ''
