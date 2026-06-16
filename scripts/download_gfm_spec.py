from __future__ import annotations

import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from urllib.request import urlopen

VERSION = '0.29'
URL = 'https://github.github.com/gfm/'
DESTINATION = Path(__file__).resolve().parent.parent / 'tests' / 'fixtures' / f'gfm-{VERSION}.json'


class GFMExampleParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.examples: list[dict[str, str | int]] = []
        self.section = ''
        self._heading_tag = ''
        self._heading: list[str] = []
        self._example_number: int | None = None
        self._example_depth = 0
        self._code_language = ''
        self._code: list[str] = []
        self._markdown: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag in {'h1', 'h2'}:
            self._heading_tag = tag
            self._heading = []
            return

        if tag == 'div' and attributes.get('class') == 'example':
            match = re.fullmatch(r'example-(\d+)', attributes.get('id', ''))
            if match is not None:
                self._example_number = int(match.group(1))
                self._example_depth = 1
                self._markdown = None
            return

        if self._example_number is not None and tag == 'div':
            self._example_depth += 1
            return

        if self._example_number is not None and tag == 'code':
            class_name = attributes.get('class', '')
            if class_name in {'language-markdown', 'language-html'}:
                self._code_language = class_name.removeprefix('language-')
                self._code = []

    def handle_endtag(self, tag: str) -> None:
        if tag == self._heading_tag:
            self.section = normalize_section(''.join(self._heading))
            self._heading_tag = ''
            self._heading = []
            return

        if self._code_language and tag == 'code':
            value = ''.join(self._code).replace('→', '\t')
            if self._code_language == 'markdown':
                self._markdown = value
            elif self._markdown is not None and self._example_number is not None:
                self.examples.append(
                    {
                        'markdown': self._markdown,
                        'html': value,
                        'example': self._example_number,
                        'section': self.section,
                    }
                )
            self._code_language = ''
            self._code = []
            return

        if self._example_number is not None and tag == 'div':
            self._example_depth -= 1
            if self._example_depth == 0:
                self._example_number = None
                self._markdown = None

    def handle_data(self, data: str) -> None:
        if self._heading_tag:
            self._heading.append(data)
        if self._code_language:
            self._code.append(data)

    def handle_entityref(self, name: str) -> None:
        self._append_charref(f'&{name};')

    def handle_charref(self, name: str) -> None:
        self._append_charref(f'&#{name};')

    def _append_charref(self, value: str) -> None:
        if self._heading_tag:
            self._heading.append(unescape(value))
        if self._code_language:
            self._code.append(unescape(value))


def normalize_section(value: str) -> str:
    value = re.sub(r'\s+', ' ', value).strip()
    return re.sub(r'^(\d+(?:\.\d+)*)(?=[A-Za-z])', r'\1 ', value)


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(URL, timeout=30) as response:
        html = response.read().decode('utf-8')

    parser = GFMExampleParser()
    parser.feed(html)
    DESTINATION.write_text(json.dumps(parser.examples, ensure_ascii=False, indent=2) + '\n')
    print(f'wrote {len(parser.examples)} examples to {DESTINATION}')


if __name__ == '__main__':
    main()
