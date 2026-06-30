from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, TypedDict

FIXTURES_DIR = Path(__file__).parent / 'fixtures'
TEXT_FIXTURE_FIELDS = (
    'asciidoc',
    'html',
    'html_directives',
    'html_options',
    'input',
    'markdown',
    'roundtrip_html',
    'rules',
    'rst',
)
TEXT_FIXTURE_SECTION_RE = re.compile(
    r'^\.(' + '|'.join(TEXT_FIXTURE_FIELDS) + r')\n',
    re.MULTILINE,
)
TEXT_FIXTURE_START_RE = re.compile(r'^## (?P<name>[^\n]+)\n\n````````fixture\n', re.MULTILINE)
TEXT_FIXTURE_END_RE = re.compile(r'^````````\n(?=\n## |\Z)', re.MULTILINE)
TEXT_FIXTURE_ESCAPED_MARKER_RE = re.compile(
    r'^\\\.(' + '|'.join(TEXT_FIXTURE_FIELDS) + r')$',
    re.MULTILINE,
)
TEXT_FIXTURE_JSON_FIELDS = {'html_directives', 'html_options', 'roundtrip_html', 'rules'}


class SpecExample(TypedDict):
    markdown: str
    html: str
    example: int
    section: str


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES_DIR / name).read_text(encoding='utf-8'))


def load_text_fixture(name: str) -> list[dict[str, Any]]:
    """Load Markdown-style fixture cases.

    A section consumes one structural trailing newline before the next marker.
    Add a blank line before the next marker when the fixture value itself must
    end with a newline. Prefix literal section marker lines with a backslash,
    for example ``\\.html``.
    """
    text = (FIXTURES_DIR / name).read_text(encoding='utf-8')
    return parse_text_fixture(text, source=name)


def parse_text_fixture(text: str, *, source: str = '<fixture>') -> list[dict[str, Any]]:
    """Parse Markdown-style fixture text."""
    examples: list[dict[str, Any]] = []
    starts = list(TEXT_FIXTURE_START_RE.finditer(text))

    for index, match in enumerate(starts):
        name = match.group('name')
        next_match = starts[index + 1] if index + 1 < len(starts) else None
        end_match = TEXT_FIXTURE_END_RE.search(text, match.end())
        if end_match is None:
            raise ValueError(f'{source}: fixture case {name!r} is missing a closing fence')
        if next_match is not None and next_match.start() < end_match.start():
            next_name = next_match.group('name')
            raise ValueError(f'{source}: fixture case {name!r} is missing a closing fence before {next_name!r}')

        example: dict[str, Any] = {'name': name}
        body = text[match.end() : end_match.start()]
        sections = list(TEXT_FIXTURE_SECTION_RE.finditer(body))
        if not sections:
            raise ValueError(f'{source}: fixture case {name!r} does not define any sections')
        if body[: sections[0].start()].strip():
            raise ValueError(f'{source}: fixture case {name!r} has content before its first section')

        for index, section in enumerate(sections):
            key = section.group(1)
            if key in example:
                raise ValueError(f'{source}: fixture case {name!r} defines section {key!r} more than once')
            start = section.end()
            end = sections[index + 1].start() if index + 1 < len(sections) else len(body)
            value = body[start:end]
            if value.endswith('\n'):
                value = value[:-1]
            if key in TEXT_FIXTURE_JSON_FIELDS:
                example[key] = json.loads(value)
            else:
                example[key] = TEXT_FIXTURE_ESCAPED_MARKER_RE.sub(r'.\1', value)

        examples.append(example)

    return examples
