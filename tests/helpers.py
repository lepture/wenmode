from __future__ import annotations

import json
from pathlib import Path
from typing import Any, TypedDict

FIXTURES_DIR = Path(__file__).parent / 'fixtures'


class SpecExample(TypedDict):
    markdown: str
    html: str
    example: int
    section: str


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding='utf-8'))
