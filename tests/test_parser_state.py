from __future__ import annotations

import re

import pytest

from wenmode import Parser, Wenmode
from wenmode.nodes import Node, Root
from wenmode.rules import (
    AtxHeading,
    BlockCandidate,
    Blockquote,
    BlockRule,
    Footnote,
    Link,
    NodeTransform,
    RootTransform,
    Rule,
)
from wenmode.state import BlockState, StateKey, StateStore

TERMS = StateKey('tests.terms', lambda: {})
TERM_RE = re.compile(r'^[ \t]{0,3}@term\[(?P<label>[^\]]+)]:[ \t]*(?P<title>.*)$')


class Glossary(Rule):
    def __init__(self) -> None:
        super().__init__('glossary')
        self.root_transforms = [GlossaryTransform()]


class TermDefinition(BlockRule):
    def __init__(self) -> None:
        super().__init__('term_definition', r'[ \t]{0,3}@term\[')

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Node | None:
        term = TERM_RE.match(state.line.rstrip('\r\n'))
        if term is None:
            return None

        state.store.get(TERMS)[term.group('label')] = term.group('title')
        state.advance()
        return None


Glossary.required_rules = [TermDefinition]


class GlossaryTransform(RootTransform):
    name = 'glossary'

    def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
        root.data = {'terms': dict(state.store.get(TERMS))}


def test_state_store_sets_scalar_values() -> None:
    key = StateKey('tests.scalar', lambda: 0)
    store = StateStore()

    store.set(key, store.get(key) + 1)

    assert store.get(key) == 1


def test_parser_reuses_reference_state_per_parse() -> None:
    app = Wenmode([Link])

    assert app.render('[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'
    assert app.render('[x]\n') == '<p>[x]</p>\n'
    assert not hasattr(app.parser, 'references')
    assert not hasattr(app.parser, '_state_stack')


def test_custom_extension_state_uses_state_store() -> None:
    app = Wenmode([Glossary, Blockquote])

    assert 'term_definition' in app.parser.rules

    root = app.parse('> @term[nested]: Nested\n\n@term[root]: Root\n\ntext\n')
    assert root.data == {'terms': {'nested': 'Nested', 'root': 'Root'}}
    assert not hasattr(BlockState([]), 'references')
    assert not hasattr(BlockState([]), 'footnotes')
    assert not hasattr(BlockState([]), 'abbreviations')

    assert app.parse('text\n').data == {'terms': {}}


def test_deferred_inline_callbacks_and_state_store_are_per_parse() -> None:
    values = StateKey('tests.deferred_values', lambda: [])

    class DeferredRule(Rule):
        def __init__(self) -> None:
            super().__init__('deferred_rule')
            self.root_transforms = [DeferredTransform()]

    class DeferredTransform(RootTransform):
        name = 'deferred_transform'
        defer_inlines = True

        def prepare(self, parser: Parser, root: Root, state: BlockState) -> None:
            def record_resolved_text() -> None:
                paragraph = root.children[0]
                first_child = getattr(paragraph, 'children', [])[0]
                state.store.get(values).append(getattr(first_child, 'value', ''))

            state.defer_inline_callback(record_resolved_text)

        def transform(self, parser: Parser, root: Root, state: BlockState) -> None:
            root.data = {'values': list(state.store.get(values))}

    app = Wenmode([DeferredRule])

    assert app.parse('first\n').data == {'values': ['first']}
    assert app.parse('second\n').data == {'values': ['second']}


def test_deferred_node_transform_callbacks_bind_each_transform() -> None:
    class MarkerTransform(NodeTransform):
        defer_inlines = True

        def __init__(self, marker: str) -> None:
            self.marker = marker
            self.name = f'marker:{marker}'

        def transform(self, parser: Parser, node: Node, state: BlockState) -> None:
            if node.data is None:
                node.data = {}
            node.data.setdefault('markers', []).append(self.marker)

    app = Wenmode([AtxHeading(transforms=[MarkerTransform('first'), MarkerTransform('second')]), Link])
    root = app.parse('# [Title][ref]\n\n[ref]: /url\n')

    heading = root.children[0]
    assert heading.data == {'markers': ['first', 'second']}
    assert heading.to_ast()['children'] == [
        {'type': 'link', 'url': '/url', 'children': [{'type': 'text', 'value': 'Title'}]},
    ]


def test_parser_binds_footnote_definitions_to_root() -> None:
    app = Wenmode([Footnote])
    root = app.parse('a[^one]\n\n[^one]: note\n')

    assert root.footnote_definitions is not None
    assert list(root.footnote_definitions) == ['one']
    assert root.footnote_definitions['one'].label == 'one'


def test_parser_skips_root_footnote_definitions_without_footnote_rule() -> None:
    app = Wenmode([AtxHeading])
    root = app.parse('# Title\n\n[^one]: note\n')

    assert root.footnote_definitions is None


def test_parser_reuses_footnote_state_per_parse() -> None:
    app = Wenmode([Footnote])

    assert 'data-footnote-ref' in app.render('[^one]: note\n\na[^one]\n')
    assert app.render('a[^one]\n') == '<p>a[^one]</p>\n'


@pytest.mark.parametrize('initial', [None, False, [], {}])
def test_state_store_initializes_falsey_values_once_per_store_and_returns_updates(initial: object) -> None:
    calls = 0

    def factory() -> object:
        nonlocal calls
        calls += 1
        return initial

    store = StateStore()
    key = StateKey('tests.cached_falsey', factory)
    assert store.get(key) is initial
    assert store.get(key) is initial
    assert calls == 1
    store.set(key, 'updated')
    assert store.get(key) == 'updated'
    assert calls == 1
    assert StateStore().get(key) is initial
    assert calls == 2


def test_state_store_factory_key_error_propagates_without_caching_failure() -> None:
    calls = 0
    failure = KeyError('factory failure')

    def factory() -> int:
        nonlocal calls
        calls += 1
        raise failure

    store = StateStore()
    key = StateKey('tests.factory_failure', factory)
    for _ in range(2):
        with pytest.raises(KeyError, match='factory failure') as raised:
            store.get(key)
        assert raised.value is failure
    assert calls == 2


def test_nested_content_scopes_measure_depth_when_entered_after_construction() -> None:
    state = BlockState([], depth=1)
    outer = state.nested_content()
    inner = state.nested_content()
    state.depth = 3

    with outer:
        assert state.content_depth == 4
        with inner:
            assert state.content_depth == 5
        assert state.content_depth == 4
    assert state.content_depth == 3
    assert state._deferred.active_depth is None


def test_nested_content_exception_restores_inline_context_and_deferred_origin_depth() -> None:
    state = BlockState([], defer_inlines=True)
    scope = state.nested_content()
    state._deferred.active_depth = 4
    state._deferred.in_inline = True
    parser = Parser([Link])
    parser.max_container_depth = 5

    with pytest.raises(RuntimeError, match='scope failure'):
        with scope:
            assert state.content_depth == 5
            assert not state._deferred.in_inline
            nodes = parser.parse_inlines('[x](/u)', state)
            with state.nested_content():
                assert state.content_depth == 6
                raise RuntimeError('scope failure')
    assert state._deferred.active_depth == 4
    assert state._deferred.in_inline
    assert len(state._deferred.pending_inlines) == 1
    assert state._deferred.pending_inlines[0][3] == 5
    parser._inline_parser.resolve_pending(state)
    assert [node.to_ast() for node in nodes] == [{'type': 'text', 'value': '[x](/u)'}]
    assert state._deferred.active_depth == 4
    assert state._deferred.in_inline
    assert not state._deferred.inline_sources
