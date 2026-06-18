from __future__ import annotations

import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
DOC_EXAMPLE_FILES = [
    ROOT / 'README.md',
    ROOT / 'docs' / 'index.md',
    ROOT / 'docs' / 'usage.md',
    ROOT / 'docs' / 'security.md',
    ROOT / 'docs' / 'recipes.md',
]

PYTHON_BLOCK_RE = re.compile(r'^```python\n(?P<code>.*?)(?:\n)?^```', re.MULTILINE | re.DOTALL)
SKIP_SNIPPETS = (
    'from fastapi',
    'from flask',
    'from django',
    'send(',
)


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


@pytest.mark.parametrize(('label', 'code'), iter_runnable_python_blocks())
def test_documentation_python_examples(label: str, code: str, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(ROOT)
    namespace = {'__name__': f'docs_example_{label}'}
    exec(compile(code, label, 'exec'), namespace)
