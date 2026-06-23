from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path
from types import ModuleType
from typing import cast

from . import __version__
from .plugins import (
    abbr,
    definition_list,
    fenced_directive,
    frontmatter,
    inline_role,
    insert,
    mark,
    math,
    ruby,
    spoiler,
    subscript,
    superscript,
)
from .presets import commonmark, github, streaming
from .renderers import HTMLRenderer, MarkdownRenderer, RSTRenderer
from .rules.base import Rule
from .wenmode import Wenmode

RuleList = Sequence[type[Rule] | Rule]

PRESETS: dict[str, RuleList] = {
    'commonmark': cast(RuleList, commonmark),
    'github': cast(RuleList, github),
    'streaming': cast(RuleList, streaming),
}

BUILTIN_PLUGINS: dict[str, ModuleType] = {
    'abbr': abbr,
    'definition_list': definition_list,
    'fenced_directive': fenced_directive,
    'frontmatter': frontmatter,
    'inline_role': inline_role,
    'insert': insert,
    'mark': mark,
    'math': math,
    'ruby': ruby,
    'spoiler': spoiler,
    'subscript': subscript,
    'superscript': superscript,
}


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='wenmode', description='Parse and render Markdown with Wenmode.')
    parser.add_argument('--version', action='version', version=f'wenmode {__version__}')

    commands = parser.add_subparsers(dest='command', required=True)

    render = commands.add_parser('render', help='Render Markdown to HTML, Markdown, or reStructuredText.')
    add_source_argument(render)
    add_preset_argument(render)
    add_plugin_argument(render)
    render.add_argument(
        '--format',
        choices=('html', 'markdown', 'rst'),
        default='html',
        help='Output format. Defaults to html.',
    )
    render.add_argument(
        '--unsafe-html',
        action='store_true',
        help='Allow raw HTML passthrough in HTML output. Only use with trusted or separately sanitized input.',
    )
    render.add_argument(
        '--unsafe-urls',
        action='store_true',
        help='Allow unsafe link and image URL schemes in HTML output. Only use with trusted input.',
    )
    render.add_argument('-o', '--output', help='Write output to a file instead of stdout.')

    ast = commands.add_parser('ast', help='Parse Markdown and print the AST as JSON.')
    add_source_argument(ast)
    add_preset_argument(ast)
    add_plugin_argument(ast)
    ast.add_argument('--positions', action='store_true', help='Include source positions in AST output.')
    ast.add_argument('--indent', type=int, default=2, help='JSON indentation level. Defaults to 2.')
    ast.add_argument('-o', '--output', help='Write output to a file instead of stdout.')

    return parser


def add_source_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        'source', nargs='?', default='-', help='Markdown file to read, or - for stdin. Defaults to stdin.'
    )


def add_preset_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '-p',
        '--preset',
        choices=tuple(PRESETS),
        default='commonmark',
        help='Markdown preset to use. Defaults to commonmark.',
    )


def add_plugin_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        '--plugin',
        action='append',
        choices=tuple(BUILTIN_PLUGINS),
        default=None,
        metavar='PLUGIN',
        help='Built-in plugin to enable. Repeat to enable multiple plugins.',
    )


def read_source(source: str) -> str:
    if source == '-':
        return sys.stdin.read()
    return Path(source).read_text(encoding='utf-8')


def write_output(text: str, output: str | None) -> None:
    if output is None:
        sys.stdout.write(text)
        return
    Path(output).write_text(text, encoding='utf-8')


def configure_standard_streams() -> None:
    """Use UTF-8 for CLI stdio when the active streams support reconfiguration."""
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        reconfigure = getattr(stream, 'reconfigure', None)
        if not callable(reconfigure):
            continue
        try:
            reconfigure(encoding='utf-8')
        except (OSError, ValueError):
            continue


def create_renderer(
    output_format: str,
    unsafe_html: bool = False,
    unsafe_urls: bool = False,
) -> HTMLRenderer | MarkdownRenderer | RSTRenderer:
    if output_format == 'html':
        return HTMLRenderer(escape=not unsafe_html, sanitize_urls=not unsafe_urls)
    if unsafe_html or unsafe_urls:
        raise ValueError('--unsafe-html and --unsafe-urls can only be used with --format html')
    if output_format == 'markdown':
        return MarkdownRenderer()
    if output_format == 'rst':
        return RSTRenderer()
    raise ValueError(f'unsupported output format: {output_format}')


def resolve_builtin_plugins(names: Sequence[str] | None) -> list[ModuleType]:
    return [BUILTIN_PLUGINS[name] for name in names or ()]


def run_render(args: argparse.Namespace) -> int:
    source = read_source(str(args.source))
    renderer = create_renderer(
        str(args.format),
        unsafe_html=bool(args.unsafe_html),
        unsafe_urls=bool(args.unsafe_urls),
    )
    wenmode = Wenmode(
        PRESETS[str(args.preset)],
        renderer=renderer,
        plugins=resolve_builtin_plugins(cast(Sequence[str] | None, args.plugin)),
    )
    output = wenmode.render(source)
    write_output(output, args.output)
    return 0


def run_ast(args: argparse.Namespace) -> int:
    source = read_source(str(args.source))
    wenmode = Wenmode(
        PRESETS[str(args.preset)],
        plugins=resolve_builtin_plugins(cast(Sequence[str] | None, args.plugin)),
        positions=bool(args.positions),
    )
    root = wenmode.parse(source)
    output = json.dumps(root.to_ast(), ensure_ascii=False, indent=int(args.indent)) + '\n'
    write_output(output, args.output)
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    configure_standard_streams()
    parser = create_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == 'render':
            return run_render(args)
        if args.command == 'ast':
            return run_ast(args)
    except OSError as exc:
        parser.exit(1, f'wenmode: {exc}\n')
    except ValueError as exc:
        parser.exit(2, f'wenmode: {exc}\n')

    parser.error(f'unknown command: {args.command}')
