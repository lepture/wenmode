from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_EXAMPLE_FILES = [
    ROOT / 'README.md',
    *[path for path in sorted((ROOT / 'docs').glob('*.md')) if not path.name.startswith('reference')],
]
MIGRATION_EXAMPLE_FILES = sorted((ROOT / 'docs' / 'migration').glob('*.md'))
MYST_EXAMPLE_FILES = [*DOC_EXAMPLE_FILES, *MIGRATION_EXAMPLE_FILES]

PYTHON_BLOCK_RE = re.compile(r'^```python\n(?P<code>.*?)(?:\n)?^```', re.MULTILINE | re.DOTALL)
MYST_PYTHON_BLOCK_RE = re.compile(r'^```\{code-block\}\s+python\n(?P<body>.*?)(?:\n)?^```', re.MULTILINE | re.DOTALL)
SKIP_SNIPPETS = (
    'from fastapi',
    'from flask',
    'from django',
    'send(',
    'class MyRule(InlineRule):',
    'Wenmode([PlusMark, Emphasis]',
    'parser.register_rule(Link',
    'parser.register_rules([AtxHeading',
)


def strip_myst_code_block_options(body: str) -> str:
    lines = body.splitlines(keepends=True)
    index = 0
    while index < len(lines) and lines[index].startswith(':'):
        index += 1
    if index < len(lines) and lines[index].strip() == '':
        index += 1
    return ''.join(lines[index:])


def iter_runnable_python_blocks() -> list[object]:
    params: list[object] = []
    for path in DOC_EXAMPLE_FILES:
        text = path.read_text(encoding='utf-8')
        for index, match in enumerate(PYTHON_BLOCK_RE.finditer(text), start=1):
            code = match.group('code')
            if any(snippet in code for snippet in SKIP_SNIPPETS):
                continue
            line = text.count('\n', 0, match.start()) + 1
            label = f'{path.relative_to(ROOT)}:{line}:block-{index}'
            params.append(pytest.param(label, code, id=label))
    return params


def iter_compilable_myst_python_blocks() -> list[object]:
    params: list[object] = []
    for path in MYST_EXAMPLE_FILES:
        text = path.read_text(encoding='utf-8')
        for index, match in enumerate(MYST_PYTHON_BLOCK_RE.finditer(text), start=1):
            code = strip_myst_code_block_options(match.group('body'))
            line = text.count('\n', 0, match.start()) + 1
            label = f'{path.relative_to(ROOT)}:{line}:code-block-{index}'
            params.append(pytest.param(label, code, id=label))
    return params


@pytest.mark.parametrize(('label', 'code'), iter_runnable_python_blocks())
def test_documentation_python_examples(label: str, code: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    namespace = {'__name__': f'docs_example_{label}'}
    exec(compile(code, label, 'exec', dont_inherit=True), namespace)


@pytest.mark.parametrize(('label', 'code'), iter_compilable_myst_python_blocks())
def test_migration_python_code_blocks_compile(label: str, code: str) -> None:
    compile(code, label, 'exec', dont_inherit=True)


def test_migration_python_code_blocks_are_discovered() -> None:
    labels = [param.values[0] for param in iter_compilable_myst_python_blocks()]
    assert any(str(label).startswith('docs/migration/mistune.md:') for label in labels)
    assert any(str(label).startswith('docs/migration/python-markdown.md:') for label in labels)


def test_plugin_setup_examples_use_unified_protocol() -> None:
    setup_re = re.compile(r'def setup\((?P<signature>[^)]*)\)')
    for name in ('plugins.md', 'custom-plugins.md'):
        path = ROOT / 'docs' / name
        text = path.read_text(encoding='utf-8')
        signatures = [match.group('signature') for match in setup_re.finditer(text)]
        assert signatures
        assert all(signature.rstrip().endswith('/') for signature in signatures)
        assert all('**' not in signature for signature in signatures)
