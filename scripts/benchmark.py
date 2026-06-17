from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import markdown
import mistune
from markdown_it import MarkdownIt

from wenmode import HTMLRenderer, Parser, github

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Case:
    name: str
    text: str

    @property
    def bytes(self) -> int:
        return len(self.text.encode())


@dataclass(frozen=True)
class Target:
    name: str
    render: Callable[[str], str]


@dataclass(frozen=True)
class Result:
    target: str
    case: str
    bytes: int
    iterations: int
    best: float
    mean: float
    throughput: float
    relative: float | None = None


def load_spec_markdown(path: Path) -> str:
    examples = json.loads(path.read_text())
    return '\n\n'.join(example['markdown'] for example in examples)


def load_cases(selected: str) -> list[Case]:
    cases = {
        'readme': Case('readme', (ROOT / 'README.md').read_text()),
        'commonmark': Case(
            'commonmark',
            load_spec_markdown(ROOT / 'tests' / 'fixtures' / 'commonmark-0.31.2.json'),
        ),
        'gfm': Case('gfm', load_spec_markdown(ROOT / 'tests' / 'fixtures' / 'gfm-0.29.json')),
    }
    if selected == 'all':
        return list(cases.values())
    return [cases[selected]]


def make_targets() -> list[Target]:
    wenmode_parser = Parser(github)
    wenmode_renderer = HTMLRenderer(escape=False, sanitize_urls=False)

    mistune_renderer = mistune.create_markdown(renderer='html', plugins=['table', 'strikethrough', 'speedup'])

    python_markdown = markdown.Markdown(extensions=['tables', 'sane_lists'])

    markdown_it = MarkdownIt('commonmark', {'html': True}).enable(['table', 'strikethrough'])

    return [
        Target('wenmode', lambda text: wenmode_renderer.render(wenmode_parser.parse(text))),
        Target('mistune', mistune_renderer),
        Target('python-markdown', lambda text: python_markdown.reset().convert(text)),
        Target('markdown-it-py', markdown_it.render),
    ]


def benchmark(target: Target, case: Case, iterations: int, warmup: int) -> Result:
    for _ in range(warmup):
        target.render(case.text)

    timings = []
    rendered_size = 0
    for _ in range(iterations):
        start = time.perf_counter()
        rendered = target.render(case.text)
        timings.append(time.perf_counter() - start)
        rendered_size += len(rendered)

    if rendered_size < 0:
        raise RuntimeError('unreachable')

    best = min(timings)
    mean = statistics.fmean(timings)
    throughput = case.bytes / best / 1_000_000
    return Result(
        target=target.name,
        case=case.name,
        bytes=case.bytes,
        iterations=iterations,
        best=best,
        mean=mean,
        throughput=throughput,
    )


def add_relative_speeds(results: list[Result]) -> list[Result]:
    wenmode_by_case = {result.case: result.mean for result in results if result.target == 'wenmode'}
    updated = []
    for result in results:
        baseline = wenmode_by_case[result.case]
        updated.append(
            Result(
                target=result.target,
                case=result.case,
                bytes=result.bytes,
                iterations=result.iterations,
                best=result.best,
                mean=result.mean,
                throughput=result.throughput,
                relative=baseline / result.mean,
            )
        )
    return updated


def format_duration(seconds: float) -> str:
    if seconds < 0.001:
        return f'{seconds * 1_000_000:.1f}us'
    if seconds < 1:
        return f'{seconds * 1_000:.2f}ms'
    return f'{seconds:.3f}s'


def print_table(results: list[Result]) -> None:
    headers = ['library', 'case', 'bytes', 'iters', 'best', 'mean', 'MB/s', 'vs wenmode']
    rows = [
        [
            result.target,
            result.case,
            str(result.bytes),
            str(result.iterations),
            format_duration(result.best),
            format_duration(result.mean),
            f'{result.throughput:.2f}',
            '1.00x' if result.relative is None else f'{result.relative:.2f}x',
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Compare Markdown-to-HTML renderer throughput.')
    parser.add_argument(
        '--case',
        choices=['readme', 'commonmark', 'gfm', 'all'],
        default='all',
        help='input corpus to benchmark',
    )
    parser.add_argument('--iterations', type=int, default=10, help='timed iterations per renderer and case')
    parser.add_argument('--warmup', type=int, default=2, help='untimed warmup iterations per renderer and case')
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.iterations < 1:
        raise SystemExit('--iterations must be at least 1')
    if args.warmup < 0:
        raise SystemExit('--warmup must be at least 0')

    cases = load_cases(args.case)
    targets = make_targets()
    results = [
        benchmark(target, case, iterations=args.iterations, warmup=args.warmup)
        for case in cases
        for target in targets
    ]
    print_table(add_relative_speeds(results))


if __name__ == '__main__':
    main()
