from __future__ import annotations

import re

import pytest

from wenmode import HTMLRenderer, MarkdownRenderer, Parser, Wenmode
from wenmode.directives import Figure
from wenmode.headings import Slugger, add_heading_ids, plain_text
from wenmode.nodes import FootnoteReference, Heading, Image, Node, Root, Text
from wenmode.parser import contains_emphasis_marker, merge_text
from wenmode.renderers import BaseRenderer, DirectiveHtmlRenderer, RenderContext
from wenmode.rules import AtxHeading, BlockRule, ContinueRule, HtmlBlock, InlineRule, ReferenceDefinition, RootTransform
from wenmode.rules import Link as LinkRule
from wenmode.rules import List as ListRule
from wenmode.rules.blocks.heading import resolve_heading_id_transform
from wenmode.state import BlockState, StateStore, StreamBlockState, StreamLineBuffer
from wenmode.toc import collect_toc

from ._edge_helpers import (
    IdentifierNode,
    LaterSearchInline,
    SearchInline,
    TriggerInline,
    WrapperNode,
)


def test_base_node_state_and_protocol_edges() -> None:
    wrapper = WrapperNode(child=Text(value='child'), children=[Text(value='nested')], value='literal')
    assert wrapper.to_ast() == {
        'type': 'wrapper',
        'child': {'type': 'text', 'value': 'child'},
        'children': [{'type': 'text', 'value': 'nested'}],
        'value': 'literal',
    }

    renderer = BaseRenderer()
    context = RenderContext()
    assert renderer.render(WrapperNode(value='x'), context) == 'x'
    assert list(renderer.render_iter([WrapperNode(value='a'), WrapperNode(value='b')])) == ['a', 'b']
    assert renderer.render(Node(type='unknown')) == ''

    assert BlockState(['\n']).first_nonblank_from_current() is None
    store = StateStore()
    pending: list[tuple[list[Node], str]] = []
    callbacks: list[object] = []
    stream_state = StreamBlockState(
        StreamLineBuffer(['\n']),
        store=store,
        pending_inlines=pending,
        pending_inline_callbacks=callbacks,  # type: ignore[arg-type]
    )
    assert stream_state.store is store
    assert stream_state.pending_inlines is pending
    assert stream_state.pending_inline_callbacks is callbacks
    assert stream_state.first_nonblank_from_current() is None

    html_renderer = HTMLRenderer()
    assert DirectiveHtmlRenderer.render(object(), html_renderer, Node(type='x'), html_renderer.create_context()) is None
    assert RootTransform.prepare(object(), Parser([]), Root(), BlockState([])) is None
    assert RootTransform.transform(object(), Parser([]), Root(), BlockState([])) is None


def test_base_rule_methods_and_wenmode_edges() -> None:
    block = BlockRule('block', r'x')
    cont = ContinueRule('continue')
    inline = InlineRule('inline', r'x')
    match = re.match('x', 'x')
    assert match is not None

    with pytest.raises(NotImplementedError):
        block.parse(Parser([]), BlockState(['x\n']), match)
    assert cont.matches('anything')
    with pytest.raises(NotImplementedError):
        cont.parse_paragraph_continuation(Parser([]), BlockState(['x\n']), [])
    assert inline.search('x') is not None
    with pytest.raises(NotImplementedError):
        inline.parse(Parser([]), 'x', match, BlockState([]))

    app = Wenmode(rules=[], renderer=HTMLRenderer(), directives=[Figure()])
    assert app.render('# Title\n') == '<p># Title</p>\n'
    app.register_rules([AtxHeading])
    assert app.render('# Title\n') == '<h1>Title</h1>\n'

    with pytest.raises(TypeError):
        Wenmode(renderer=MarkdownRenderer()).register_directive_renderer(Figure())


def test_heading_and_toc_helper_edges() -> None:
    root = Root(
        children=[
            Heading(depth=1, data={'id': 'existing'}, children=[Text(value='Existing')]),
            Heading(depth=2, data={}, children=[Image(alt='Alt text'), FootnoteReference(label='fn')]),
            Heading(depth=7, children=[Text(value='Skipped')]),
        ]
    )
    slugger = Slugger()

    add_heading_ids(root, slugger=slugger)

    assert root.children[0].data == {'id': 'existing'}
    assert root.children[1].data == {'id': 'alt-textfn'}
    assert (
        plain_text([Image(alt='Alt'), FootnoteReference(label='Label'), IdentifierNode(identifier='id')])
        == 'AltLabelid'
    )
    assert plain_text([Node(type='plain')]) == ''
    assert collect_toc(root, max_depth=1)[0].id == 'existing'
    assert resolve_heading_id_transform(False) == []
    assert len(resolve_heading_id_transform(True)) == 1


def test_parser_internal_edge_branches() -> None:
    Parser([LinkRule, ReferenceDefinition])
    assert list(Parser([ReferenceDefinition]).parse_iter(['[x]: /url\n'])) == []

    parser = Parser([SearchInline, LaterSearchInline, TriggerInline])
    assert parser.parse('x\n').to_ast() == {
        'type': 'root',
        'children': [{'type': 'paragraph', 'children': [{'type': 'text', 'value': 'search'}]}],
    }

    first = SearchInline()
    second = LaterSearchInline()
    parser = Parser([first, second])
    first_match = re.match('x', 'x')
    second_match = re.match('x', 'x')
    assert first_match is not None
    assert second_match is not None
    assert not parser._inline_candidate_before((0, second, second_match), (0, first, first_match))
    assert parser._inline_candidate_before((0, first, first_match), (0, second, second_match))

    with pytest.raises(RuntimeError, match='without a named group'):
        Parser([])._match_block_rule(re.match('x', 'x'))  # type: ignore[arg-type]
    unknown = re.match('(?P<missing>x)', 'x')
    assert unknown is not None
    with pytest.raises(RuntimeError, match='unknown block rule'):
        Parser([])._match_block_rule(unknown)

    list_parser = Parser([ListRule])
    list_parser.max_container_depth = 0
    assert not list_parser.is_paragraph_interrupt('- item\n', BlockState([], depth=1))
    html_parser = Parser([HtmlBlock])
    assert html_parser.is_paragraph_interrupt('<!DOCTYPE html>\n', BlockState([]))
    assert not Parser([]).is_paragraph_interrupt('# heading\n')

    assert merge_text([Text(value='a'), Text(value='b', _parse_emphasis=False)]) == [
        Text(value='a'),
        Text(value='b', _parse_emphasis=False),
    ]
    assert not contains_emphasis_marker([Text(value='*', _parse_emphasis=False), Node(type='other')])
