from __future__ import annotations

import argparse
import statistics
import time
from collections.abc import Callable
from dataclasses import dataclass

from wenmode import Wenmode
from wenmode.plugins import block_spoiler, html_container, inline_math
from wenmode.presets import commonmark
from wenmode.rules import ContainerDirective, Footnote, Table, TextDirective


@dataclass(frozen=True)
class EdgeCase:
    name: str
    category: str
    generate: Callable[[int], str]
    make_app: Callable[[bool], Wenmode]
    sizes: tuple[int, ...]


@dataclass(frozen=True)
class Result:
    case: str
    size: int
    bytes: int
    iterations: int
    best: float
    mean: float
    ns_per_unit: float
    growth: float | None
    normalized_growth: float | None


def commonmark_app(positions: bool) -> Wenmode:
    return Wenmode(commonmark, positions=positions)


def directive_app(positions: bool) -> Wenmode:
    return Wenmode([ContainerDirective], positions=positions)


def block_spoiler_app(positions: bool) -> Wenmode:
    return Wenmode(commonmark, plugins=[block_spoiler], positions=positions)


def inline_math_app(positions: bool) -> Wenmode:
    return Wenmode([], plugins=[inline_math], positions=positions)


def text_directive_app(positions: bool) -> Wenmode:
    return Wenmode([TextDirective], positions=positions)


def footnote_app(positions: bool) -> Wenmode:
    return Wenmode([Footnote], positions=positions)


def html_container_app(positions: bool) -> Wenmode:
    return Wenmode(commonmark, plugins=[html_container], positions=positions)


def table_app(positions: bool) -> Wenmode:
    return Wenmode([Table], positions=positions)


EDGE_CASES = {
    'deep-blockquote': EdgeCase(
        'deep-blockquote',
        'containers',
        lambda size: '> ' * size + 'text\n',
        commonmark_app,
        (100, 1000, 10000),
    ),
    'deep-list': EdgeCase(
        'deep-list',
        'containers',
        lambda size: '- ' * size + 'text\n',
        commonmark_app,
        (100, 1000, 10000),
    ),
    'blockquote-depth-boundary': EdgeCase(
        'blockquote-depth-boundary',
        'containers',
        lambda size: '> ' * size + 'text\n',
        commonmark_app,
        (99, 100, 101, 1000),
    ),
    'alternating-containers': EdgeCase(
        'alternating-containers',
        'containers',
        lambda size: '> - ' * size + 'text\n',
        commonmark_app,
        (64, 128, 256),
    ),
    'deep-block-spoiler': EdgeCase(
        'deep-block-spoiler',
        'containers',
        lambda size: '>! ' * size + 'text\n',
        block_spoiler_app,
        (100, 1000, 10000),
    ),
    'unmatched-links': EdgeCase(
        'unmatched-links',
        'inline',
        lambda size: '[' * size + '\n',
        commonmark_app,
        (1000, 10000, 100000),
    ),
    'nested-link-labels': EdgeCase(
        'nested-link-labels',
        'inline',
        lambda size: '[' * size + 'text' + ']' * size + '(/url)\n',
        commonmark_app,
        (200, 1000, 5000),
    ),
    'nested-image-labels': EdgeCase(
        'nested-image-labels',
        'inline',
        lambda size: '![' * size + 'text' + '](/url)' * size + '\n',
        commonmark_app,
        (200, 1000, 5000),
    ),
    'dense-emphasis': EdgeCase(
        'dense-emphasis',
        'inline',
        lambda size: '*a' * size + '\n',
        commonmark_app,
        (1000, 10000, 100000),
    ),
    'long-code-span-runs': EdgeCase(
        'long-code-span-runs',
        'inline',
        lambda size: '`' * size + 'text' + '`' * (size - 1) + '\n',
        commonmark_app,
        (1000, 10000, 100000),
    ),
    'nested-text-directives': EdgeCase(
        'nested-text-directives',
        'inline',
        lambda size: ':x[' * size + 'text' + ']' * size + '\n',
        text_directive_app,
        (100, 500, 1000),
    ),
    'invalid-inline-math-closers': EdgeCase(
        'invalid-inline-math-closers',
        'inline',
        lambda size: '$x' + '$5' * size + '\n',
        inline_math_app,
        (1000, 5000, 10000),
    ),
    'long-list-spacing': EdgeCase(
        'long-list-spacing',
        'blocks',
        lambda size: '- ' + ' ' * size + 'text\n',
        commonmark_app,
        (1000, 10000, 100000),
    ),
    'blank-list-continuations': EdgeCase(
        'blank-list-continuations',
        'blocks',
        lambda size: '- first\n' + '\n' * size + '  last\n',
        commonmark_app,
        (1000, 5000, 10000),
    ),
    'list-marker-interrupt': EdgeCase(
        'list-marker-interrupt',
        'blocks',
        lambda size: 'paragraph\n1. ' + ' ' * size + '\n',
        commonmark_app,
        (1000, 10000, 100000),
    ),
    'unclosed-fence': EdgeCase(
        'unclosed-fence',
        'blocks',
        lambda size: '```\n' + 'line\n' * size,
        commonmark_app,
        (1000, 5000, 10000),
    ),
    'nested-directives': EdgeCase(
        'nested-directives',
        'containers',
        lambda size: ':::note\n' * size + 'text\n' + ':::\n' * size,
        directive_app,
        (64, 128, 256),
    ),
    'unclosed-reference-title': EdgeCase(
        'unclosed-reference-title',
        'references',
        lambda size: '[x]: /url "\n' + 'line\n' * size + '\n[x]\n',
        commonmark_app,
        (1000, 5000, 10000),
    ),
    'footnote-blank-continuations': EdgeCase(
        'footnote-blank-continuations',
        'references',
        lambda size: '[^x]: first\n' + '\n' * size + '  second\n\n[^x]\n',
        footnote_app,
        (1000, 5000, 10000),
    ),
    'nested-html-containers': EdgeCase(
        'nested-html-containers',
        'html',
        lambda size: '<div>\n' * size + '</div>\n' * size,
        html_container_app,
        (64, 128, 256),
    ),
    'wide-table': EdgeCase(
        'wide-table',
        'tables',
        lambda size: (
            '| ' + ' | '.join(['cell'] * size) + ' |\n' + '| ' + ' | '.join(['---'] * size) + ' |\n'
        ),
        table_app,
        (100, 1000, 5000),
    ),
}


def benchmark_case(edge_case: EdgeCase, sizes: list[int], iterations: int, warmup: int, positions: bool) -> list[Result]:
    app = edge_case.make_app(positions)
    results: list[Result] = []
    previous_size: int | None = None
    previous_mean: float | None = None

    for size in sizes:
        text = edge_case.generate(size)
        for _ in range(warmup):
            app.parse(text)

        timings: list[float] = []
        for _ in range(iterations):
            started = time.perf_counter()
            app.parse(text)
            timings.append(time.perf_counter() - started)

        best = min(timings)
        mean = statistics.fmean(timings)
        if previous_size is None or previous_mean is None:
            growth = None
            normalized_growth = None
        else:
            growth = mean / previous_mean
            normalized_growth = growth / (size / previous_size)
        results.append(
            Result(
                case=edge_case.name,
                size=size,
                bytes=len(text.encode()),
                iterations=iterations,
                best=best,
                mean=mean,
                ns_per_unit=mean / size * 1_000_000_000,
                growth=growth,
                normalized_growth=normalized_growth,
            )
        )
        previous_size = size
        previous_mean = mean

    return results


def format_duration(seconds: float) -> str:
    if seconds < 0.001:
        return f'{seconds * 1_000_000:.1f}us'
    if seconds < 1:
        return f'{seconds * 1_000:.2f}ms'
    return f'{seconds:.3f}s'


def format_ratio(value: float | None) -> str:
    if value is None:
        return '-'
    return f'{value:.2f}x'


def print_table(results: list[Result]) -> None:
    headers = ['case', 'size', 'bytes', 'iters', 'best', 'mean', 'ns/unit', 'growth', 'normalized']
    rows = [
        [
            result.case,
            str(result.size),
            str(result.bytes),
            str(result.iterations),
            format_duration(result.best),
            format_duration(result.mean),
            f'{result.ns_per_unit:.1f}',
            format_ratio(result.growth),
            format_ratio(result.normalized_growth),
        ]
        for result in results
    ]
    widths = [len(header) for header in headers]
    for row in rows:
        widths = [max(width, len(cell)) for width, cell in zip(widths, row)]
    print('  '.join(header.ljust(width) for header, width in zip(headers, widths)))
    print('  '.join('-' * width for width in widths))
    for row in rows:
        print('  '.join(cell.ljust(width) for cell, width in zip(row, widths)))


def parse_sizes(value: str) -> list[int]:
    try:
        sizes = sorted({int(item) for item in value.split(',')})
    except ValueError as exc:
        raise argparse.ArgumentTypeError('sizes must be comma-separated integers') from exc
    if not sizes or sizes[0] < 1:
        raise argparse.ArgumentTypeError('sizes must contain positive integers')
    return sizes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Benchmark adversarial Markdown parser inputs.')
    parser.add_argument('--case', default='all', choices=['all', *EDGE_CASES], help='edge case to benchmark')
    parser.add_argument(
        '--category',
        default='all',
        choices=['all', *sorted({edge_case.category for edge_case in EDGE_CASES.values()})],
        help='edge-case category to benchmark',
    )
    parser.add_argument('--sizes', type=parse_sizes, help='override comma-separated case sizes')
    parser.add_argument('--iterations', type=int, default=5)
    parser.add_argument('--warmup', type=int, default=1)
    parser.add_argument('--positions', action='store_true', help='enable source position tracking')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.iterations < 1:
        raise SystemExit('--iterations must be at least 1')
    if args.warmup < 0:
        raise SystemExit('--warmup must be at least 0')
    if args.case != 'all' and args.category != 'all':
        raise SystemExit('--case and --category cannot be combined')

    if args.case != 'all':
        cases = [EDGE_CASES[args.case]]
    elif args.category != 'all':
        cases = [edge_case for edge_case in EDGE_CASES.values() if edge_case.category == args.category]
    else:
        cases = list(EDGE_CASES.values())
    results = [
        result
        for edge_case in cases
        for result in benchmark_case(
            edge_case,
            args.sizes or list(edge_case.sizes),
            args.iterations,
            args.warmup,
            args.positions,
        )
    ]
    print_table(results)


if __name__ == '__main__':
    main()
