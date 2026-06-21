from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from io import StringIO

import pytest

from wenmode import __version__, cli
from wenmode.cli import main


def test_cli_renders_file(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('# Hello\n', encoding='utf-8')

    assert main(['render', str(source)]) == 0

    captured = capsys.readouterr()
    assert captured.out == '<h1>Hello</h1>\n'
    assert captured.err == ''


def test_cli_renders_stdin(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, 'stdin', StringIO('**Hi**\n'))

    assert main(['render']) == 0

    captured = capsys.readouterr()
    assert captured.out == '<p><strong>Hi</strong></p>\n'
    assert captured.err == ''


def test_cli_renders_github_preset(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('| A |\n| - |\n| B |\n', encoding='utf-8')

    assert main(['render', '--preset', 'github', str(source)]) == 0

    captured = capsys.readouterr()
    assert '<table>' in captured.out
    assert '<td>B</td>' in captured.out


def test_cli_render_enables_builtin_plugins(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('Inline $x + y$ and ==marked==.\n', encoding='utf-8')

    assert main(['render', '--plugin', 'math', '--plugin', 'mark', str(source)]) == 0

    captured = capsys.readouterr()
    assert captured.out == (
        '<p>Inline <span class="math math-inline">x + y</span> and <mark>marked</mark>.</p>\n'
    )


def test_cli_renders_rst_format(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('# Hello\n', encoding='utf-8')

    assert main(['render', '--format', 'rst', str(source)]) == 0

    captured = capsys.readouterr()
    assert captured.out == 'Hello\n=====\n'


def test_cli_renders_markdown_format(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('# Hello\n\nA **bold** word.\n', encoding='utf-8')

    assert main(['render', '--format', 'markdown', str(source)]) == 0

    captured = capsys.readouterr()
    assert captured.out == '# Hello\n\nA **bold** word\\.\n'


def test_cli_html_output_escapes_raw_html_and_sanitizes_urls_by_default(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('<div>div</div>\n\n[bad](javascript:alert(1))\n', encoding='utf-8')

    assert main(['render', str(source)]) == 0

    captured = capsys.readouterr()
    assert captured.out == '&lt;div&gt;div&lt;/div&gt;\n<p><a>bad</a></p>\n'


def test_cli_html_output_allows_explicit_unsafe_passthrough(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('<div>div</div>\n\n[bad](javascript:alert(1))\n', encoding='utf-8')

    assert main(['render', '--unsafe-html', '--unsafe-urls', str(source)]) == 0

    captured = capsys.readouterr()
    assert captured.out == '<div>div</div>\n<p><a href="javascript:alert(1)">bad</a></p>\n'


def test_cli_rejects_unsafe_html_options_for_non_html_output(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('# Hello\n', encoding='utf-8')

    with pytest.raises(SystemExit) as exc_info:
        main(['render', '--format', 'markdown', '--unsafe-html', str(source)])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert '--unsafe-html and --unsafe-urls can only be used with --format html' in captured.err


def test_cli_reports_missing_input_file(tmp_path, capsys) -> None:
    missing = tmp_path / 'missing.md'

    with pytest.raises(SystemExit) as exc_info:
        main(['render', str(missing)])

    captured = capsys.readouterr()
    assert exc_info.value.code == 1
    assert 'wenmode:' in captured.err
    assert str(missing) in captured.err


def test_cli_rejects_unknown_plugin(capsys) -> None:
    with pytest.raises(SystemExit) as exc_info:
        main(['render', '--plugin', 'unknown'])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "invalid choice: 'unknown'" in captured.err


def test_create_renderer_rejects_unknown_format() -> None:
    with pytest.raises(ValueError, match='unsupported output format: xml'):
        cli.create_renderer('xml')


def test_cli_reports_unexpected_unknown_command(monkeypatch) -> None:
    class FakeParser:
        def parse_args(self, argv):
            return argparse.Namespace(command='unknown')

        def error(self, message):
            raise SystemExit(message)

    monkeypatch.setattr(cli, 'create_parser', FakeParser)

    with pytest.raises(SystemExit) as exc_info:
        cli.main([])

    assert str(exc_info.value) == 'unknown command: unknown'


def test_cli_prints_ast_json_with_positions(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('A **bold**.\n', encoding='utf-8')

    assert main(['ast', '--positions', str(source)]) == 0

    captured = capsys.readouterr()
    ast = json.loads(captured.out)
    assert ast['type'] == 'root'
    assert ast['children'][0]['children'][1]['type'] == 'strong'
    assert ast['children'][0]['children'][1]['position'] == {
        'start': {'line': 1, 'column': 3, 'offset': 2},
        'end': {'line': 1, 'column': 11, 'offset': 10},
    }


def test_cli_ast_enables_builtin_plugins(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    source.write_text('Inline $x + y$.\n', encoding='utf-8')

    assert main(['ast', '--plugin', 'math', str(source)]) == 0

    captured = capsys.readouterr()
    ast = json.loads(captured.out)
    inline_math = ast['children'][0]['children'][1]
    assert inline_math == {'type': 'inlineMath', 'value': 'x + y'}


def test_cli_writes_output_file(tmp_path, capsys) -> None:
    source = tmp_path / 'input.md'
    output = tmp_path / 'output.html'
    source.write_text('# Hello\n', encoding='utf-8')

    assert main(['render', str(source), '--output', str(output)]) == 0

    captured = capsys.readouterr()
    assert captured.out == ''
    assert output.read_text(encoding='utf-8') == '<h1>Hello</h1>\n'


def test_python_module_entrypoint() -> None:
    completed = subprocess.run(
        [sys.executable, '-m', 'wenmode', '--version'],
        check=True,
        capture_output=True,
        text=True,
    )

    assert completed.stdout == f'wenmode {__version__}\n'


def test_python_module_entrypoint_writes_utf8_stdout_on_non_utf8_locale(tmp_path) -> None:
    source = tmp_path / 'input.md'
    source.write_text('# Title ★ star\n', encoding='utf-8')
    env = {**os.environ, 'PYTHONIOENCODING': 'cp1251'}

    completed = subprocess.run(
        [sys.executable, '-m', 'wenmode', 'render', str(source)],
        check=True,
        capture_output=True,
        env=env,
    )

    assert completed.stdout.decode('utf-8') == '<h1>Title ★ star</h1>\n'
    assert completed.stderr == b''
