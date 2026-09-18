from __future__ import annotations

from wenmode import Parser, Wenmode
from wenmode.nodes import Node, Text
from wenmode.rules import InlineCandidate, InlineRule
from wenmode.state import BlockState


class CountingSearchRule(InlineRule):
    def __init__(self, name: str, pattern: str, replacement: str, accept: bool = True) -> None:
        super().__init__(name=name, pattern=pattern)
        self.replacement = replacement
        self.accept = accept
        self.search_calls = 0

    def search_candidate(self, text: str, pos: int = 0) -> InlineCandidate | None:
        self.search_calls += 1
        return super().search_candidate(text, pos)

    def parse(
        self, parser: Parser, text: str, candidate: InlineCandidate, state: BlockState
    ) -> tuple[Node | None, int]:
        if not self.accept:
            return None, candidate.start
        assert candidate.match is not None
        return Text(value=self.replacement), candidate.match.end()


def test_missing_search_rule_does_not_rescan_after_other_matches() -> None:
    frequent = CountingSearchRule('frequent', 'a', 'A')
    missing = CountingSearchRule('missing', 'q', 'Q')

    assert Wenmode([frequent, missing]).render('a' * 100) == '<p>' + 'A' * 100 + '</p>\n'
    assert missing.search_calls == 1


def test_future_search_candidate_is_preserved_until_consumed() -> None:
    frequent = CountingSearchRule('frequent', 'a', 'A')
    future = CountingSearchRule('future', 'z', 'Z')

    assert Wenmode([frequent, future]).render('aaaaaz end') == '<p>AAAAAZ end</p>\n'
    assert future.search_calls == 2


def test_search_candidate_inside_consumed_span_is_invalidated() -> None:
    span = CountingSearchRule('span', 'abqz', 'SPAN')
    inner = CountingSearchRule('inner', 'q', 'Q')

    assert Wenmode([span, inner]).render('abqzq') == '<p>SPANQ</p>\n'
    assert inner.search_calls == 2


def test_declined_search_candidates_preserve_same_position_rule_order() -> None:
    declined = CountingSearchRule('declined', 'aa', 'DECLINED', accept=False)
    accepted = CountingSearchRule('accepted', 'aa', 'ACCEPTED')

    assert Wenmode([declined, accepted]).render('aaaa') == '<p>ACCEPTEDACCEPTED</p>\n'


def test_declined_search_candidate_does_not_hide_later_candidate() -> None:
    declined = CountingSearchRule('declined', 'a', 'DECLINED', accept=False)
    later = CountingSearchRule('later', 'z', 'Z')

    assert Wenmode([declined, later]).render('aaaaaz') == '<p>aaaaaZ</p>\n'
    assert later.search_calls == 1


def test_search_cache_is_not_shared_between_documents() -> None:
    missing = CountingSearchRule('missing', 'q', 'Q')
    app = Wenmode([missing])

    assert app.render('nothing') == '<p>nothing</p>\n'
    assert app.render('q') == '<p>Q</p>\n'
    assert missing.search_calls == 2
