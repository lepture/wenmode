from __future__ import annotations

from types import SimpleNamespace

import pytest

from tests import test_performance as performance
from wenmode.rules import HardBreak


def stub_parse_times(monkeypatch: pytest.MonkeyPatch, small: list[float], large: list[float]) -> list[str]:
    durations = {'small': iter(small), 'large': iter(large)}
    calls: list[str] = []

    def parse_time(markdown: str, rules: object, plugins: object = (), positions: bool = False) -> float:
        calls.append(markdown)
        return next(durations[markdown])

    monkeypatch.setattr(performance, 'parse_time', parse_time)
    return calls


def test_scaling_accepts_linear_timings(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = stub_parse_times(monkeypatch, [1.0, 1.1, 0.9, 1.01, 1.02], [2.0, 2.1, 1.9, 2.01, 2.02])

    performance.assert_scales_nearly_linearly(lambda size: 'small' if size == 1000 else 'large', [], 1000, 2000)

    assert len(calls) == 10


@pytest.mark.parametrize('small, large, outlier', [(0.020427, 0.040, 0.100522), (0.002682, 0.0054, 0.059441)])
def test_scaling_tolerates_one_isolated_large_sample_pause(
    small: float, large: float, outlier: float, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls = stub_parse_times(monkeypatch, [small] * 5, [outlier, large, large, large, large])

    performance.assert_scales_nearly_linearly(lambda size: 'small' if size == 1000 else 'large', [], 1000, 2000)

    assert calls.count('small') == calls.count('large') == 5


def test_scaling_rejects_sustained_quadratic_timings_with_original_bounds(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = stub_parse_times(monkeypatch, [1.0] * 5, [4.0] * 5)

    with pytest.raises(AssertionError, match='medians 1.000000s -> 4.000000s') as failure:
        performance.assert_scales_nearly_linearly(lambda size: 'small' if size == 1000 else 'large', [], 1000, 2000)

    assert len(calls) == 10
    assert 'small samples=[1.0, 1.0, 1.0, 1.0, 1.0]' in str(failure.value)
    assert 'large samples=[4.0, 4.0, 4.0, 4.0, 4.0]' in str(failure.value)
    assert 'ratio=3.5, slack=0.02' in str(failure.value)


def test_scaling_preserves_caller_ratio_and_slack(monkeypatch: pytest.MonkeyPatch) -> None:
    stub_parse_times(monkeypatch, [1.0] * 5, [2.506] * 5)

    with pytest.raises(AssertionError, match='ratio=2.5, slack=0.005'):
        performance.assert_scales_nearly_linearly(
            lambda size: 'small' if size == 1000 else 'large', [], 1000, 2000, ratio=2.5, slack=0.005
        )


def test_scaling_alternates_five_pairs_and_reuses_iterable_rules_and_plugins(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[int] = []
    factory_sizes: list[int] = []
    plugin = object()

    def factory(size: int) -> str:
        factory_sizes.append(size)
        return 'x' * size

    def parse_time(markdown, rules, plugins=(), positions=False):
        assert tuple(rules) == (HardBreak,)
        assert tuple(plugins) == (plugin,)
        assert positions is True
        calls.append(len(markdown))
        return float(len(markdown))

    monkeypatch.setattr(performance, 'parse_time', parse_time)
    performance.assert_scales_nearly_linearly(factory, iter([HardBreak]), 2, 4, plugins=iter([plugin]), positions=True)

    assert factory_sizes == [2, 4]
    assert calls == [2, 4, 4, 2, 2, 4, 4, 2, 2, 4]


def test_parse_time_keeps_parser_and_plugin_setup_outside_timed_parse(monkeypatch: pytest.MonkeyPatch) -> None:
    events: list[str] = []
    plugin = object()
    ticks = iter([10.0, 12.0])

    class Parser:
        def __init__(self, rules, positions=False):
            assert rules == (HardBreak,)
            assert positions is True
            events.append('construct')

        def use(self, installed):
            assert installed is plugin
            events.append('plugin')

        def parse(self, markdown):
            assert markdown == 'source'
            events.append('parse')

    def clock() -> float:
        events.append('clock')
        return next(ticks)

    monkeypatch.setattr(performance, 'Wenmode', Parser)
    monkeypatch.setattr(performance, 'time', SimpleNamespace(perf_counter=clock))

    assert performance.parse_time('source', (HardBreak,), plugins=[plugin], positions=True) == 2.0
    assert events == ['construct', 'plugin', 'clock', 'parse', 'clock']
