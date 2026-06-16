from __future__ import annotations

from wenmode import HTMLRenderer, Wenmode, github
from wenmode.rules import AtxHeading, Blockquote, Emphasis, FencedCode, Footnote, Image, Link, List, SetextHeading


def render(parser: Wenmode, markdown: str) -> str:
    return HTMLRenderer().render(parser.parse(markdown))


def test_parser_reuses_reference_state_per_parse() -> None:
    parser = Wenmode([Link])

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p><a href="/url">x</a></p>\n'
    assert render(parser, '[x]\n') == '<p>[x]</p>\n'
    assert not hasattr(parser, 'references')
    assert not hasattr(parser, '_state_stack')


def test_reference_definitions_are_plain_text_without_reference_consumers() -> None:
    parser = Wenmode([AtxHeading])

    assert render(parser, '[x]: /url\n\n[x]\n') == '<p>[x]: /url</p>\n<p>[x]</p>\n'
    assert isinstance(parser.rules, dict)


def test_fence_like_text_is_not_protected_without_fenced_code_rule() -> None:
    parser = Wenmode([Link])

    assert render(parser, '```\n\n[x]: /url\n\n[x]\n') == '<p>```</p>\n<p><a href="/url">x</a></p>\n'


def test_blockquote_depth_is_limited() -> None:
    parser = Wenmode([Blockquote])
    parser.max_container_depth = 8

    assert 'a' in render(parser, '> ' * 1000 + 'a\n')


def test_list_depth_is_limited() -> None:
    parser = Wenmode([List])
    parser.max_container_depth = 8

    markdown = ''.join('  ' * index + '- a\n' for index in range(64))
    assert 'a' in render(parser, markdown)


def test_deep_list_fast_path_at_depth_limit() -> None:
    parser = Wenmode([List])
    parser.max_container_depth = 1

    markdown = ''.join('  ' * index + '- a\n' for index in range(1000))
    assert 'a' in render(parser, markdown)


def test_emphasis_rule_enables_strong_and_emphasis() -> None:
    parser = Wenmode([Emphasis])

    assert render(parser, '*a* **b**\n') == '<p><em>a</em> <strong>b</strong></p>\n'


def test_setext_heading_rule_owns_paragraph_continuation() -> None:
    assert render(Wenmode([SetextHeading]), 'a\n-\n') == '<h2>a</h2>\n'
    assert render(Wenmode([]), 'a\n-\n') == '<p>a\n-</p>\n'


def test_image_keeps_reference_definitions_enabled() -> None:
    parser = Wenmode([Image])

    assert render(parser, '[x]: /img.png\n\n![x]\n') == '<p><img src="/img.png" alt="x" /></p>\n'


def test_footnote_resolves_later_definition() -> None:
    parser = Wenmode([Footnote])

    assert (
        render(parser, 'a[^one]\n\n[^one]: note\n')
        == '<p>a<sup><a href="#user-content-fn-one" id="user-content-fnref-one" '
        'data-footnote-ref aria-describedby="footnote-label">1</a></sup></p>\n'
        '<section data-footnotes class="footnotes">\n'
        '<h2 class="sr-only" id="footnote-label">Footnotes</h2>\n'
        '<ol>\n'
        '<li id="user-content-fn-one">\n'
        '<p>note <a href="#user-content-fnref-one" data-footnote-backref '
        'class="data-footnote-backref" aria-label="Back to content">&#8617;</a></p>\n'
        '</li>\n'
        '</ol>\n'
        '</section>\n'
    )


def test_footnote_resolves_earlier_definition() -> None:
    parser = Wenmode([Footnote])

    assert 'href="#user-content-fn-one"' in render(parser, '[^one]: note\n\na[^one]\n')


def test_missing_footnote_definition_leaves_text() -> None:
    parser = Wenmode([Footnote])

    assert render(parser, 'a[^missing]\n') == '<p>a[^missing]</p>\n'


def test_parser_reuses_footnote_state_per_parse() -> None:
    parser = Wenmode([Footnote])

    assert 'data-footnote-ref' in render(parser, '[^one]: note\n\na[^one]\n')
    assert render(parser, 'a[^one]\n') == '<p>a[^one]</p>\n'


def test_footnote_definitions_are_plain_text_without_footnote_rule() -> None:
    parser = Wenmode([Link])

    assert render(parser, '[^one]: note\n\n[^one]\n') == '<p>[^one]: note</p>\n<p>[^one]</p>\n'


def test_duplicate_footnote_definitions_use_first_definition() -> None:
    parser = Wenmode([Footnote])

    html = render(parser, '[^one]: first\n\n[^one]: second\n\na[^one]\n')

    assert '<p>first <a href="#user-content-fnref-one"' in html
    assert 'second' not in html


def test_github_preset_enables_footnotes_with_links() -> None:
    parser = Wenmode(github)

    html = render(parser, '[link](/url) and a[^one]\n\n[^one]: note\n')

    assert '<a href="/url">link</a>' in html
    assert 'data-footnote-ref' in html


def test_footnote_rule_does_not_depend_on_link_order() -> None:
    parser = Wenmode([Link, Footnote])

    assert 'data-footnote-ref' in render(parser, 'a[^one]\n\n[^one]: note\n')
