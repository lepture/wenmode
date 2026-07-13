from __future__ import annotations

import argparse
import hashlib
import statistics
import tarfile
import tempfile
import time
import urllib.request
from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Callable

import commonmark as commonmark_py
import markdown
import markdown2
import mistune
from markdown_it import MarkdownIt
from marko.ext.gfm import gfm as marko_gfm

from wenmode import HTMLRenderer, Wenmode, __version__
from wenmode.plugins import (
    abbr,
    block_math,
    block_spoiler,
    definition_list,
    fenced_directive,
    frontmatter,
    github_alert,
    heading_ids,
    inline_math,
    inline_role,
    inline_spoiler,
    insert,
    mark,
    ruby,
    subscript,
    superscript,
)
from wenmode.presets import commonmark, github
from wenmode.rules import ContainerDirective, LeafDirective, Table, TextDirective

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'docs'
RUST_BOOK_TARBALL = 'https://github.com/rust-lang/book/archive/refs/heads/main.tar.gz'
PROGIT_TARBALL = 'https://github.com/progit/progit/archive/refs/heads/master.tar.gz'
GITHUB_DOCS_TARBALL = 'https://github.com/github/docs/archive/refs/heads/main.tar.gz'
USER_AGENT = 'wenmode-benchmark'
CACHE_DIR = Path(tempfile.gettempdir()) / 'wenmode-benchmark'


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
    version: str
    render: Callable[[str], str]


@dataclass(frozen=True)
class Result:
    target: str
    version: str
    case: str
    bytes: int
    iterations: int
    best: float
    mean: float
    throughput: float
    relative: float | None = None


def docs_markdown_paths() -> list[Path]:
    return sorted(DOCS.glob('*.md'))


def load_markdown_files_case(name: str, paths: list[Path]) -> Case:
    parts = []
    for path in paths:
        label = path_label(path)
        parts.append(f'<!-- {label} -->\n\n{path.read_text()}')
    return Case(name, '\n\n'.join(parts))


def load_docs_case() -> Case:
    return load_markdown_files_case('docs', docs_markdown_paths())


def load_local_file_case(selected: str) -> Case | None:
    path = Path(selected).expanduser()
    if not path.is_absolute():
        path = ROOT / path
    if not path.is_file():
        return None
    return Case(path_label(path.with_suffix('')), path.read_text())


def path_label(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def load_archive_case(name: str, url: str, include: Callable[[str], bool]) -> Case:
    parts = []
    with tarfile.open(cached_archive(url), mode='r:gz') as tar:
        members = sorted(
            (
                member
                for member in tar.getmembers()
                if member.isfile() and len(Path(member.name).parts) > 1 and include(archive_relative_path(member.name))
            ),
            key=lambda member: member.name,
        )
        for member in members:
            extracted = tar.extractfile(member)
            if extracted is None:
                continue
            label = archive_relative_path(member.name)
            parts.append(f'<!-- {label} -->\n\n{extracted.read().decode(errors="replace")}')

    return Case(name, '\n\n'.join(parts))


def cached_archive(url: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path = CACHE_DIR / archive_filename(url)
    if not path.exists():
        request = urllib.request.Request(url, headers={'User-Agent': USER_AGENT})
        with urllib.request.urlopen(request, timeout=120) as response:
            temporary_path = path.with_name(path.name + '.tmp')
            temporary_path.write_bytes(response.read())
            temporary_path.replace(path)
    return path


def archive_filename(url: str) -> str:
    digest = hashlib.sha256(url.encode()).hexdigest()[:16]
    name = url.rstrip('/').rsplit('/', 1)[-1]
    return f'{digest}-{name}'


def archive_relative_path(path: str) -> str:
    parts = Path(path).parts
    return '/'.join(parts[1:])


def load_rust_book_case() -> Case:
    return load_archive_case(
        'rust-book', RUST_BOOK_TARBALL, lambda path: path.startswith('src/') and path.endswith('.md')
    )


def load_progit_case() -> Case:
    return load_archive_case(
        'progit', PROGIT_TARBALL, lambda path: path.startswith('en/') and path.endswith('.markdown')
    )


def load_cases(selected: str) -> list[Case]:
    cases = {'docs': load_docs_case, 'rust-book': load_rust_book_case, 'progit': load_progit_case}
    if selected == 'all':
        return [load_case() for load_case in cases.values()]

    load_case = cases.get(selected)
    if load_case is not None:
        return [load_case()]

    local_file = load_local_file_case(selected)
    if local_file is not None:
        return [local_file]

    options = [*cases, 'all', '<local-file>']
    raise SystemExit(f'unknown --case {selected!r}; choose one of: {", ".join(options)}')


def make_targets() -> list[Target]:
    # The non-Wenmode parsers are configured to match wenmode-core's feature set
    # as closely as their APIs allow: CommonMark-style parsing plus pipe tables.
    # commonmark.py does not support pipe tables, so it is included as a
    # CommonMark-only migration target.
    # wenmode-all intentionally enables many extra Wenmode plugins that are mostly
    # unused by these corpora, so it measures dispatch overhead under a broad
    # rule set rather than a syntax-equivalent comparison.
    wenmode_core = Wenmode([Table, *commonmark], HTMLRenderer(escape=False, sanitize_urls=False))
    wenmode_all = make_wenmode_all()

    mistune_renderer = mistune.create_markdown(renderer='html', plugins=['table', 'speedup'])

    python_markdown = markdown.Markdown(extensions=['tables', 'sane_lists'])

    markdown_it = MarkdownIt('commonmark', {'html': True}).enable('table')

    markdown2_renderer = markdown2.Markdown(extras=['tables'])

    commonmark_parser = commonmark_py.Parser()
    commonmark_renderer = commonmark_py.HtmlRenderer()

    def render_commonmark(text: str) -> str:
        return commonmark_renderer.render(commonmark_parser.parse(text))

    return [
        Target('wenmode-core', __version__, wenmode_core.render),
        Target('wenmode-all', __version__, wenmode_all.render),
        Target('mistune', version('mistune'), mistune_renderer),
        Target('python-markdown', version('markdown'), lambda text: python_markdown.reset().convert(text)),
        Target('markdown-it-py', version('markdown-it-py'), markdown_it.render),
        Target('markdown2', version('markdown2'), markdown2_renderer.convert),
        Target('marko', version('marko'), marko_gfm),
        Target('commonmark.py', version('commonmark'), render_commonmark),
    ]


def make_wenmode_all() -> Wenmode:
    wen = Wenmode(
        [*github, LeafDirective, ContainerDirective, TextDirective],
        HTMLRenderer(escape=False, sanitize_urls=False),
        plugins=[
            fenced_directive,
            frontmatter,
            inline_math,
            block_math,
            inline_spoiler,
            block_spoiler,
            definition_list,
            abbr,
            inline_role,
            ruby,
            mark,
            insert,
            superscript,
            subscript,
            heading_ids,
            github_alert,
        ],
    )
    return wen


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
        version=target.version,
        case=case.name,
        bytes=case.bytes,
        iterations=iterations,
        best=best,
        mean=mean,
        throughput=throughput,
    )


def add_relative_speeds(results: list[Result], baseline_target: str = 'wenmode-core') -> list[Result]:
    baseline_by_case = {result.case: result.mean for result in results if result.target == baseline_target}
    updated = []
    for result in results:
        baseline = baseline_by_case[result.case]
        updated.append(
            Result(
                target=result.target,
                version=result.version,
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
    headers = ['library', 'version', 'case', 'bytes', 'iters', 'best', 'mean', 'MB/s', 'vs core']
    rows = [
        [
            result.target,
            result.version,
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
        metavar='CASE',
        default='docs',
        help='input corpus: docs, rust-book, progit, all, or a local file path',
    )
    parser.add_argument('--iterations', type=int, default=5, help='timed iterations per renderer and case')
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
        benchmark(target, case, iterations=args.iterations, warmup=args.warmup) for case in cases for target in targets
    ]
    print_table(add_relative_speeds(results))


if __name__ == '__main__':
    main()
