from __future__ import annotations

import pytest

from wenmode import Parser, Wenmode
from wenmode.nodes import Node, Parent, Position, Text
from wenmode.plugins import block_spoiler, definition_list, fenced_directive, html_container, inline_spoiler
from wenmode.presets import commonmark, github, streaming
from wenmode.rules import BlockCandidate, BlockRule, ContainerDirective, InlineCandidate, InlineRule, TextDirective
from wenmode.state import BlockState

SCAFFOLDING = {
    'root',
    'paragraph',
    'heading',
    'listItem',
    'definitionTerm',
    'definitionDescription',
    'tableRow',
    'tableCell',
}


def content_depth(node: Node) -> int:
    if not isinstance(node, Parent):
        return 0
    own_depth = int(node.type not in SCAFFOLDING)
    return own_depth + max((content_depth(child) for child in node.children), default=0)


@pytest.mark.parametrize('preset', [commonmark, github, streaming])
@pytest.mark.parametrize('limit', [0, 1, 3, 20])
@pytest.mark.parametrize('positions', [False, True])
def test_block_inline_and_emphasis_share_one_budget(preset, limit: int, positions: bool) -> None:
    app = Wenmode(preset(), positions=positions).use(inline_spoiler)
    app.parser.max_container_depth = limit
    markdown = '> - >! *a [b](/u)* !<\n'
    root = app.parse(markdown)
    assert content_depth(root) <= limit
    assert app.parse(iter(markdown.splitlines(keepends=True))).to_ast() == root.to_ast()
    if preset is streaming:
        assert ''.join(app.stream(markdown)) == app.render(markdown)


@pytest.mark.parametrize('limit', [0, 1, 3, 20])
def test_custom_inline_nesting_has_no_extra_level(limit: int) -> None:
    app = Wenmode([TextDirective])
    app.parser.max_container_depth = limit
    root = app.parse(':x[' * 25 + 'a' + ']' * 25)
    assert content_depth(root) == limit


@pytest.mark.parametrize('deferred', [False, True])
@pytest.mark.parametrize(
    'markdown',
    [
        '> *a*\n',
        '- *a*\n',
        '>! *a*\n',
        ':::note[*label*]\n*body*\n:::\n',
        '```{note} *label*\n*body*\n```\n',
        '*term*\n: *description*\n',
    ],
)
def test_container_labels_and_shallow_content_consume_the_container_budget(markdown: str, deferred: bool) -> None:
    app = (
        Wenmode(commonmark() if deferred else streaming()).use(block_spoiler).use(fenced_directive).use(definition_list)
    )
    app.register_rule(ContainerDirective())
    app.parser.max_container_depth = 1
    root = app.parse(markdown)
    assert content_depth(root) == 1
    assert 'emphasis' not in str(root.to_ast())


def test_emphasis_cannot_wrap_an_already_saturated_link_or_spoiler() -> None:
    app = Wenmode().use(inline_spoiler)
    app.parser.max_container_depth = 1
    root = app.parse('*[a](/u)* *>! b !<*')
    assert content_depth(root) == 1
    assert app.render('*[a](/u)*') == '<p>*<a href="/u">a</a>*</p>\n'
    assert app.render('[*a*](/u)') == '<p><a href="/u">*a*</a></p>\n'


class InlineBlocks(InlineRule):
    name = 'inline_blocks'
    opener = '%'

    def parse(
        self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
    ) -> tuple[Node | None, int]:
        children = parser.parse_blocks(text[candidate.start + 1 :], state)
        return Parent(type='inlineBlocks', children=children), len(text)


class NestedBlock(BlockRule):
    name = 'nested_block'
    pattern = '@'

    def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Node:
        text = state.line[1:]
        state.advance()
        return Parent(type='nestedBlock', children=parser.parse_blocks(text, state))


@pytest.mark.parametrize('limit', [0, 1, 3, 20])
@pytest.mark.parametrize('deferred', [False, True])
def test_inline_block_inline_transitions_neither_reset_nor_double_count_depth(limit: int, deferred: bool) -> None:
    rules = [*commonmark(), InlineBlocks, NestedBlock] if deferred else [InlineBlocks, NestedBlock]
    parser = Parser(rules)
    parser.max_container_depth = limit
    root = parser.parse('@' + '%@' * 30 + 'a')
    assert content_depth(root) == limit


def test_deferred_footnote_content_retains_its_quote_and_definition_depth() -> None:
    app = Wenmode(github(), positions=True)
    app.parser.max_container_depth = 3
    root = app.parse('> [^n]: *[a](/u)*\n\n[^n]\n')
    assert content_depth(root) <= 3
    assert root.footnote_definitions is not None
    definition = root.footnote_definitions['n']
    assert content_depth(definition) == 2
    assert definition.children[0].children[0].value == '*'


def test_boundary_literal_positions_survive_deferred_nested_blocks() -> None:
    app = Wenmode(commonmark(), positions=True)
    app.parser.max_container_depth = 1
    literal = app.parse('> *a*\n').children[0].children[0].children[0]
    assert isinstance(literal, Text)
    assert literal.value == '*a*'
    assert literal.position == Position(2, 5)


def test_active_depth_restores_after_inline_to_block_failure() -> None:
    class FailsOnce(BlockRule):
        name = 'fails_once'
        pattern = '!'

        def parse(self, parser: Parser, state: BlockState, candidate: BlockCandidate) -> Node:
            raise RuntimeError('expected failure')

    parser = Parser([InlineBlocks, FailsOnce])
    parser.max_container_depth = 3
    state = BlockState([])
    with pytest.raises(RuntimeError, match='expected failure'):
        parser.parse_inlines('%!', state)
    assert state.content_depth == 0
    assert content_depth(parser.parse_inlines('%%a', state)[0]) == 2


def test_mixed_plugin_containers_use_the_same_budget() -> None:
    app = Wenmode(commonmark()).use(block_spoiler).use(fenced_directive).use(html_container)
    app.register_rule(ContainerDirective())
    app.parser.max_container_depth = 3
    markdown = ':::note\n>! ```{note}\n>! <div>\n>! *body*\n>! </div>\n>! ```\n:::\n'
    assert content_depth(app.parse(markdown)) <= 3


@pytest.mark.parametrize(
    'markdown',
    ['>! *body*\n', ':::note[*label*]\n*body*\n:::\n', '@%a\n', '*term*\n: *description*\n', '[^n]: *body*\n'],
)
def test_zero_depth_runs_no_block_or_continuation_container_rules(markdown: str) -> None:
    app = Wenmode(github(), positions=True).use(block_spoiler).use(definition_list)
    app.register_rules([ContainerDirective(), NestedBlock(), InlineBlocks()])
    app.parser.max_container_depth = 0
    root = app.parse(markdown)
    assert content_depth(root) == 0
    assert all(child.type == 'paragraph' for child in root.children)
    assert all(child.position is not None for child in root.children)


def test_deferred_dispatch_restores_active_depth_and_source_after_nested_failure() -> None:
    captured_states: list[BlockState] = []

    class FailingInline(InlineRule):
        name = 'failing_inline'
        opener = '!'

        def parse(
            self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
        ) -> tuple[Node | None, int]:
            captured_states.append(state)
            raise RuntimeError('expected deferred failure')

    parser = Parser([*commonmark(), InlineBlocks, FailingInline], positions=True)
    parser.max_container_depth = 3
    with pytest.raises(RuntimeError, match='expected deferred failure'):
        parser.parse('%!')
    state = captured_states[0]
    assert state.content_depth == state.depth == 1
    assert state._deferred.active_depth is None
    assert not state._deferred.in_inline
    assert state.inline_source_for('%!') is None
    assert state.inline_source_for('!') is None
    assert content_depth(parser.parse_inlines('%%a', state)[0]) == 2


def test_deferred_dispatch_keeps_the_resolving_state_depth_floor() -> None:
    from wenmode.rules import Link

    parser = Parser([Link])
    parser.max_container_depth = 1
    state = BlockState([], depth=1)
    nodes: list[Node] = []
    state.defer_inline_parse(nodes, '[a](/u)', None, depth=0)
    parser._inline_parser.resolve_pending(state)
    assert nodes == [Text(value='[a](/u)')]
    assert state._deferred.active_depth is None
    assert not state._deferred.in_inline


@pytest.mark.parametrize('limit', [0, 1, 2, 3, 20])
@pytest.mark.parametrize('positions', [False, True])
def test_tables_and_abbreviation_transforms_share_the_semantic_budget(limit: int, positions: bool) -> None:
    from wenmode.plugins import abbr

    app = Wenmode(github(), positions=positions).use(abbr)
    app.parser.max_container_depth = limit
    markdown = '*[HTML]: HyperText\n\n| *HTML* | HTML |\n| --- | --- |\n| HTML | **HTML** |\n\n> HTML\n'
    root = app.parse(markdown)
    stack = [(root, 0)]
    while stack:
        node, depth = stack.pop()
        depth += int(isinstance(node, Parent) and node.type not in SCAFFOLDING)
        assert depth <= limit
        if isinstance(node, Parent):
            stack.extend((child, depth) for child in node.children)
    assert app.parse(iter(markdown.splitlines(keepends=True))).to_ast() == root.to_ast()


def test_streaming_table_cells_keep_the_table_origin_depth_and_positions() -> None:
    app = Wenmode(streaming(), positions=True)
    app.parser.max_container_depth = 1
    markdown = '| *a* |\n| --- |\n| *b* |\n'
    root = app.parse(markdown)
    assert root.children[0].children[0].children[0].children[0].value == '*a*'
    assert ''.join(app.stream(markdown)) == app.render(markdown)


@pytest.mark.parametrize('deferred', [False, True])
def test_table_cell_failure_restores_shared_depth_and_inline_source(deferred: bool) -> None:
    from wenmode.rules import Link, Table

    states: list[BlockState] = []

    class Fails(InlineRule):
        name = 'table_failure'
        opener = '!'

        def parse(self, parser, text, candidate, state):
            states.append(state)
            raise RuntimeError('table failure')

    parser = Parser([Table, Fails, *([Link] if deferred else [])], positions=True)
    with pytest.raises(RuntimeError, match='table failure'):
        parser.parse('| ! |\n| --- |\n')
    state = states[0]
    assert state.content_depth == state.depth == 0
    assert state._deferred.active_depth is None
    assert not state._deferred.in_inline
    assert state.inline_source_for('!') is None
