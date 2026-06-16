from __future__ import annotations

import html
import re
from urllib.parse import quote

ESCAPABLE = r'!"#$%&\'()*+,\-./:;<=>?@\[\\\]^_`{|}~'


def normalize_label_text(value: str) -> str:
    value = re.sub(rf'\\([{ESCAPABLE}])', r'\1', value)
    return html.unescape(value)


def normalize_label(value: str) -> str:
    return re.sub(r'\s+', ' ', normalize_label_text(value).strip()).casefold()


def normalize_uri_text(value: str) -> str:
    return quote(normalize_label_text(value), safe="/:?#@!$&'()*+,;=%._~-")
