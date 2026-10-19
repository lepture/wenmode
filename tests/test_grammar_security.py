from __future__ import annotations

import pytest

from wenmode import Wenmode
from wenmode.ast import from_ast
from wenmode.utils.text import decode_character_references


@pytest.mark.parametrize(
    'raw, expected',
    [
        ('&#9999999;', '\ufffd'),
        ('&#xD800;', '\ufffd'),
        ('&#x110000;', '\ufffd'),
        ('&#0000065;', 'A'),
        ('&#x000041;', 'A'),
        ('&#99999999;', '&#99999999;'),
        ('&#x0000041;', '&#x0000041;'),
        ('&notanentity;', '&notanentity;'),
        ('&#１２;', '&#１２;'),
    ],
)
def test_shared_entity_grammar_in_inline_text_and_normalization(raw: str, expected: str) -> None:
    assert decode_character_references(raw) == expected
    assert Wenmode().parse(raw).children[0].children[0].value == expected


def test_huge_decimal_entity_stays_literal_without_integer_conversion() -> None:
    raw = '&#' + '9' * 10000 + ';'
    assert decode_character_references(raw) == raw
    assert Wenmode().parse(raw).children[0].children[0].value == raw


@pytest.mark.parametrize(
    'invalid',
    [
        {'type': 'heading', 'depth': True},
        {'type': 'heading', 'depth': 7},
        {'type': 'list', 'start': '1'},
        {'type': 'text', 'value': {}},
        {'type': 'unknown'},
    ],
)
def test_invalid_ast_root_does_not_construct_expensive_descendants(invalid, monkeypatch: pytest.MonkeyPatch) -> None:
    import wenmode.ast as ast_module

    calls = 0
    construct = ast_module._construct_node

    def counted(*args):
        nonlocal calls
        calls += 1
        return construct(*args)

    monkeypatch.setattr(ast_module, '_construct_node', counted)
    invalid = {**invalid, 'children': [{'type': 'text', 'value': 'expensive'}] * 1000}
    with pytest.raises((ValueError, TypeError)):
        from_ast(invalid, unknown='error')
    assert calls == 0


def test_invalid_late_ast_child_is_rejected_before_earlier_children_are_constructed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import wenmode.ast as ast_module

    def unexpected(*args):
        raise AssertionError('children must be validated before construction')

    monkeypatch.setattr(ast_module, '_construct_node', unexpected)
    with pytest.raises(TypeError, match='entries must be nodes'):
        from_ast({'type': 'root', 'children': [{'type': 'text', 'value': 'a'}] * 1000 + [0]})


@pytest.mark.parametrize('codepoint', [1, 11, 127, 128, 159, 65535, 1114111])
def test_numeric_entities_preserve_valid_unicode_scalars(codepoint: int) -> None:
    raw = f'&#{codepoint};'
    assert decode_character_references(raw) == chr(codepoint)


def test_ast_child_cardinality_exceeds_node_budget_before_accessing_entries() -> None:
    class UnreadableList(list):
        def __iter__(self):
            raise AssertionError('budget should reject before scanning entries')

    with pytest.raises(ValueError, match='maximum node count'):
        from_ast({'type': 'root', 'children': UnreadableList([{}] * 100)}, max_nodes=5)


@pytest.mark.parametrize('raw', ['<?a\nb?>', '<![CDATA[a\nb]]>', '<!lower a\nb>'])
def test_literal_ended_html_can_span_lines_and_lowercase_declarations(raw: str) -> None:
    from wenmode.rules import RawHtml

    node = Wenmode([RawHtml]).parse('x ' + raw).children[0].children[1]
    assert node.type == 'html'
    assert node.value == raw


def test_failed_html_endings_are_scanned_once_in_raw_dispatch_and_link_brackets() -> None:
    from wenmode.rules import Link, RawHtml
    from wenmode.rules.inlines.link import build_closing_bracket_map
    from wenmode.state import BlockState

    class CountedText(str):
        endings = 0

        def find(self, sub, *args):
            if sub == '-->':
                self.endings += 1
            return super().find(sub, *args)

    text = CountedText('x <!-- unfinished ' * 1000)
    app = Wenmode([RawHtml, Link])
    state = BlockState([])
    app.parser.parse_inlines(text, state)
    assert text.endings == 1
    text = CountedText('x <!-- unfinished ' * 1000)
    build_closing_bracket_map(text, BlockState([]))
    # GFM scans its first double-hyphen terminator instead.
    assert text.endings == 0


def test_repeated_autolink_parse_and_custom_search_overrides_are_preserved() -> None:
    from wenmode import Parser
    from wenmode.rules import ExtendedAutolink
    from wenmode.state import BlockState

    text = 'https://example.com a@example.com'
    parser = Parser([ExtendedAutolink])
    state = BlockState([])
    first = [node.to_ast() for node in parser.parse_inlines(text, state)]
    assert [node.to_ast() for node in parser.parse_inlines(text, state)] == first
    assert parser.parse_inlines('plain', state)[0].value == 'plain'

    class Disabled(ExtendedAutolink):
        def search_candidate(self, text, pos=0):
            return None

    assert Parser([Disabled]).parse_inlines(text, BlockState([]))[0].value == text


@pytest.mark.parametrize(
    'raw, valid',
    [
        ('<!---->', True),
        ('<!-->', False),
        ('<!--->', False),
        ('<!--a--b-->', False),
        ('<!--a--->', False),
        ('<!--a-->', True),
    ],
)
def test_gfm_comment_terminal_grammar(raw: str, valid: bool) -> None:
    from wenmode.rules import RawHtml

    children = Wenmode([RawHtml(comment_style='gfm')]).parse('x ' + raw).children[0].children
    assert any(node.type == 'html' for node in children) is valid


def test_html_container_pairing_scans_each_state_once_including_streaming(monkeypatch: pytest.MonkeyPatch) -> None:
    from wenmode.plugins import html_container
    from wenmode.presets import streaming

    original = html_container.parse_container_opener
    calls = 0

    def counted(line):
        nonlocal calls
        calls += 1
        return original(line)

    monkeypatch.setattr(html_container, 'parse_container_opener', counted)
    markdown = '<div>\nx\n\n' * 80
    app = Wenmode(streaming()).use(html_container)
    app.render(iter(markdown.splitlines(keepends=True)))
    assert calls < 5 * 80
    assert app.render('<DiV>\n\na\n\n</dIv>\n').startswith('&lt;DiV&gt;')


def test_roles_reject_name_grammar_before_search_and_preserve_longer_closer_prefix() -> None:
    from wenmode.plugins.inline_role import _parse_role

    class NoFind(str):
        def find(self, *args):
            raise AssertionError('invalid names must fail before searching')

    assert _parse_role(NoFind('{a ' * 1000), 0) is None
    assert _parse_role('{a}``b```', 0) == ('a', 'b', 8, 5, 6)


def test_legacy_delimiters_index_escaped_candidates_once(monkeypatch: pytest.MonkeyPatch) -> None:
    from wenmode import Parser
    from wenmode.rules import Strikethrough, delimiters
    from wenmode.state import BlockState

    checks = 0
    original = delimiters.is_escaped

    def counted(text, index):
        nonlocal checks
        checks += 1
        return original(text, index)

    monkeypatch.setattr(delimiters, 'is_escaped', counted)
    Parser([Strikethrough]).parse_inlines(r'\~a ' * 1000, BlockState([]))
    assert checks <= 1000


def test_gfm_table_splits_unescaped_pipe_inside_inline_code() -> None:
    from wenmode.presets import github

    html = Wenmode(github()).render('| a | b |\n| --- | --- |\n| `x|y` | z |\n')
    assert '<td>`x</td>\n<td>y`</td>' in html


@pytest.mark.parametrize('override', ['url', 'email'])
def test_autolink_two_argument_search_overrides_can_forward_to_super(override: str) -> None:
    from wenmode.rules import ExtendedAutolink

    class URLOverride(ExtendedAutolink):
        def search_url(self, text, pos):
            return super().search_url(text, pos)

    class EmailOverride(ExtendedAutolink):
        def search_email(self, text, pos):
            return super().search_email(text, pos)

    app = Wenmode([URLOverride if override == 'url' else EmailOverride])
    assert app.render('https://example.com a@example.com').count('<a href=') == 2


@pytest.mark.parametrize('token', ['https://example.com ', 'a@example.com ', 'a.www.x@y.com '])
def test_autolink_prefix_and_email_searches_cover_source_linearly(token: str) -> None:
    from wenmode import Parser
    from wenmode.rules import ExtendedAutolink
    from wenmode.state import BlockState

    work = 0

    class PrefixProbe(str):
        def find(self, sub, start=0):
            nonlocal work
            found = super().find(sub, start)
            work += (found + len(sub) if found != -1 else len(self)) - start
            return found

    class EmailProbe(str):
        scanned = 0

        def lower(self):
            return PrefixProbe(super().lower())

        def find(self, sub, start=0, end=None):
            limit = len(self) if end is None else end
            found = super().find(sub, start, limit)
            if sub == '@':
                self.scanned += (found + 1 if found != -1 else limit) - start
            return found

    text = EmailProbe(token * 1000)
    nodes = Parser([ExtendedAutolink]).parse_inlines(text, BlockState([]))
    assert sum(node.type == 'link' for node in nodes) == 1000
    assert 0 < work < len(text) * 20
    assert text.scanned < len(text) * 3


def test_descending_role_fence_failures_build_one_next_greater_run_index() -> None:
    from wenmode.plugins.inline_role import _parse_role
    from wenmode.state import BlockState

    class Probe(str):
        searches = 0

        def find(self, *args):
            self.searches += 1
            return super().find(*args)

    parts = ['{a}' + '`' * length + 'x ' for length in range(150, 0, -1)]
    text = Probe(''.join(parts))
    state = BlockState([])
    start = 0
    for part in parts:
        assert _parse_role(text, start, state) is None
        start += len(part)
    assert text.searches == 1


@pytest.mark.parametrize('opener, ending', [('<!--', '-->'), ('<?', '?>'), ('<![CDATA[', ']]>'), ('<!lower', '>')])
def test_each_missing_html_terminal_is_searched_once_per_source(opener: str, ending: str) -> None:
    from wenmode import Parser
    from wenmode.rules import RawHtml
    from wenmode.rules.inlines.link import build_closing_bracket_map
    from wenmode.state import BlockState

    class Probe(str):
        searches = 0

        def find(self, sub, *args):
            if sub == ending:
                self.searches += 1
            return super().find(sub, *args)

    text = Probe(('x ' + opener + ' unfinished ') * 500)
    Parser([RawHtml]).parse_inlines(text, BlockState([]))
    assert text.searches == 1
    if opener != '<!--':
        text = Probe(text)
        build_closing_bracket_map(text)
        assert text.searches == 1


@pytest.mark.parametrize('plugin, marker', [('subscript', '~'), ('superscript', '^')])
def test_legacy_script_plugins_share_indexed_escaped_closers(
    plugin: str, marker: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    from wenmode.rules import delimiters

    checks = 0
    original = delimiters.is_escaped

    def counted(text, index):
        nonlocal checks
        checks += 1
        return original(text, index)

    monkeypatch.setattr(delimiters, 'is_escaped', counted)
    app = Wenmode([]).use(importlib.import_module('wenmode.plugins.' + plugin))
    app.parse(('\\' + marker + 'a ') * 500)
    assert checks <= 500


def test_entity_decoder_integrates_urls_titles_references_and_preserves_raw_attributes() -> None:
    from wenmode.plugins import html_container

    app = Wenmode()
    assert app.render('[a](/&#xD800; "&#x80;")') == '<p><a href="/%EF%BF%BD" title="\x80">a</a></p>\n'
    assert app.render('[&#xD800;]\n\n[\ufffd]: /ok\n') == '<p><a href="/ok">\ufffd</a></p>\n'
    node = Wenmode().use(html_container).parse('<div x="&#128;">\n\na\n\n</div>\n').children[0]
    assert node.attributes == {'x': '&#128;'}


def test_html_tags_keep_arbitrary_quoted_attribute_lengths() -> None:
    from wenmode.rules import RawHtml

    value = '<a x="' + 'a' * 10000 + '">'
    assert Wenmode([RawHtml]).parse('x ' + value).children[0].children[1].value == value
    assert all(node.type != 'html' for node in Wenmode([RawHtml]).parse('x ' + value[:-2]).children[0].children)


def test_github_uses_commonmark_declarations_and_gfm_comments() -> None:
    from wenmode.presets import github

    children = Wenmode(github()).parse('x <!lower body> <!---->').children[0].children
    assert [node.value for node in children if node.type == 'html'] == ['<!lower body>', '<!---->']


def test_autolink_ascii_scheme_search_keeps_unicode_offsets() -> None:
    from wenmode.rules import ExtendedAutolink

    html = Wenmode([ExtendedAutolink]).render('İ https://example.com ı maılto:a@example.com')
    assert '<a href="https://example.com">https://example.com</a>' in html
    assert 'maılto:<a href="mailto:a@example.com">a@example.com</a>' in html


def test_autolink_positions_follow_original_unicode_source_after_case_expansion() -> None:
    from wenmode.rules import ExtendedAutolink

    text = 'İ https://example.com'
    link = Wenmode([ExtendedAutolink], positions=True).parse(text).children[0].children[1]
    assert link.position.start == 2
    assert link.position.end == len(text)
    assert link.children[0].position == link.position


def test_plain_autolink_source_does_not_prepare_document_cache(monkeypatch: pytest.MonkeyPatch) -> None:
    from wenmode._parser.state import BlockState
    from wenmode.rules.inlines.extended_autolink import ExtendedAutolink

    state = BlockState([])
    monkeypatch.setattr(state.store, 'get', lambda key: pytest.fail('ordinary text needs no autolink cache'))
    assert ExtendedAutolink()._search_candidate('ordinary 中文 text with no autolink', 0, state) is None


@pytest.mark.parametrize('node_type, registered', [('html', False), ('htmlContainer', True), ('htmlContainer', False)])
def test_reserved_html_metadata_is_rejected_before_descendant_construction(
    node_type: str, registered: bool, monkeypatch: pytest.MonkeyPatch
) -> None:
    import wenmode.ast as ast_module
    from wenmode.plugins.html_container import HtmlContainerNode

    calls = 0
    construct = ast_module._construct_node

    def counted(*args):
        nonlocal calls
        calls += 1
        return construct(*args)

    monkeypatch.setattr(ast_module, '_construct_node', counted)
    ast = {'type': node_type, 'data': {'escaped': True}, 'children': [{'type': 'text', 'value': 'expensive'}] * 1000}
    if node_type == 'html':
        ast['value'] = '&lt;div&gt;'
    else:
        ast.update(name='div', opening='&lt;div&gt;', closing='&lt;/div&gt;')
    nodes = [HtmlContainerNode] if registered else None
    with pytest.raises(ValueError, match='data.escaped.*internal metadata'):
        from_ast(ast, nodes=nodes)
    assert calls == 0

    trusted = {**ast, 'children': ast['children'][:1]}
    assert from_ast(trusted, nodes=nodes, allow_internal_metadata=True).to_ast() == trusted


def test_autolink_initial_rejection_preserves_custom_compiled_email_pattern() -> None:
    from wenmode.rules import ExtendedAutolink

    class ShortEmail(ExtendedAutolink):
        pattern = r'[a-z]+@[a-z]+'

    assert Wenmode([ShortEmail]).render('a@b') == '<p><a href="a@b">a@b</a></p>\n'


def test_autolink_initial_rejection_preserves_custom_search_for_plain_source() -> None:
    from wenmode.rules import ExtendedAutolink

    class Custom(ExtendedAutolink):
        pattern = r'custom'

        def search_url(self, text, pos):
            return self.compiled.search(text, pos)

    assert Wenmode([Custom]).render('custom') == '<p><a href="custom">custom</a></p>\n'
