from __future__ import annotations

from pathlib import Path
from urllib.request import urlopen

VERSION = '0.31.2'
URL = f'https://spec.commonmark.org/{VERSION}/spec.json'
DESTINATION = Path(__file__).resolve().parent.parent / 'tests' / 'fixtures' / f'commonmark-{VERSION}.json'


def main() -> None:
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    with urlopen(URL, timeout=30) as response:
        DESTINATION.write_bytes(response.read())
    print(f'wrote {DESTINATION}')


if __name__ == '__main__':
    main()
