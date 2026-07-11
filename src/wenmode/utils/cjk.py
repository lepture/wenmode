from __future__ import annotations

import unicodedata

ASCII_PUNCTUATION = frozenset('!"#$%&\'()*+,-./:;<=>?@[\\]^_`{|}~')


def is_punctuation(char: str) -> bool:
    # CommonMark 0.31.2: a Unicode punctuation character is in the P or S general category.
    # ASCII fast path (the common case) avoids the unicodedata lookup; it is exactly
    # equivalent to the P/S test for ASCII, where the only such characters are these.
    if char.isascii():
        return char in ASCII_PUNCTUATION
    return unicodedata.category(char)[0] in ('P', 'S')


def is_cjk_character(char: str) -> bool:
    if not char or char == '\n':
        return False
    codepoint = ord(char)
    return (
        unicodedata.east_asian_width(char) in ('W', 'F', 'H')
        or 0x1100 <= codepoint <= 0x11FF
        or 0xA960 <= codepoint <= 0xA97F
        or 0xAC00 <= codepoint <= 0xD7AF
        or 0xD7B0 <= codepoint <= 0xD7FF
    )


def is_ideographic_variation_selector(char: str) -> bool:
    codepoint = ord(char)
    return 0xE0100 <= codepoint <= 0xE01EF


def is_cjk_punctuation(char: str) -> bool:
    return is_punctuation(char) and is_cjk_character(char)


def is_non_cjk_punctuation(char: str) -> bool:
    return is_punctuation(char) and not is_cjk_punctuation(char)
