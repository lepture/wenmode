from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

from wenmode import RSTRenderer, Wenmode
from wenmode.presets import github

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = ROOT / 'README.md'
DEFAULT_OUTPUT = ROOT / 'README.rst'
HEADER_RE = re.compile(r'\A<div align="center">\n(?P<header>.*?)\n</div>\n*', re.DOTALL)
BADGE_RE = re.compile(
    r'^\[!\[(?P<alt>[^\]]+)\]\((?P<image>[^)]+)\)\]\((?P<target>[^)]+)\)\s*$',
    re.MULTILINE,
)


@dataclass(frozen=True)
class Badge:
    alt: str
    image: str
    target: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Build README.rst for PyPI from README.md.')
    parser.add_argument('--source', type=Path, default=DEFAULT_SOURCE, help='Markdown README path.')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT, help='Generated reStructuredText README path.')
    parser.add_argument('--title', default='Wenmode', help='Top-level title for the generated README.')
    parser.add_argument(
        '--check',
        action='store_true',
        help='Fail if the generated output differs from the existing output file.',
    )
    return parser.parse_args()


def build_pypi_readme(markdown: str, title: str = 'Wenmode') -> str:
    badges, body = split_github_header(markdown)
    rendered_body = Wenmode(github, renderer=RSTRenderer()).render(body).lstrip()
    return rst_header(title, badges) + rendered_body


def split_github_header(markdown: str) -> tuple[list[Badge], str]:
    match = HEADER_RE.match(markdown)
    if match is None:
        raise ValueError('README.md must start with the GitHub HTML header block')

    badges = [
        Badge(
            alt=badge.group('alt'),
            image=badge.group('image'),
            target=badge.group('target'),
        )
        for badge in BADGE_RE.finditer(match.group('header'))
    ]
    if not badges:
        raise ValueError('README.md header block must contain at least one badge')

    return badges, markdown[match.end() :].lstrip()


def rst_header(title: str, badges: list[Badge]) -> str:
    lines = [
        title,
        '=' * len(title),
        '',
        ' '.join(f'|{badge_name(badge.alt)}|' for badge in badges),
        '',
    ]
    for badge in badges:
        name = badge_name(badge.alt)
        lines.extend(
            [
                f'.. |{name}| image:: {badge.image}',
                f'   :target: {badge.target}',
                f'   :alt: {badge.alt}',
                '',
            ]
        )
    return '\n'.join(lines) + '\n'


def badge_name(alt: str) -> str:
    return ' '.join(alt.split()).replace('|', r'\|')


def main() -> int:
    args = parse_args()
    source = args.source.read_text(encoding='utf-8')
    output = build_pypi_readme(source, title=args.title)

    if args.check:
        current = args.output.read_text(encoding='utf-8') if args.output.exists() else ''
        if current != output:
            raise SystemExit(f'{args.output} is out of date; run {Path(__file__).as_posix()}')
        return 0

    args.output.write_text(output, encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
