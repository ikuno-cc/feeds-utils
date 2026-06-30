import unicodedata
import re


class NormalizerOptions:
    def __init__(
        self,
        lowercase: bool = True,
        unicode_form: str = "NFC",
        collapse_whitespace: bool = True,
        strip_punctuation: bool = False,
        strip_numbers: bool = False,
        normalize_quotes: bool = True,
        normalize_dashes: bool = True,
        normalize_ellipsis: bool = True,
        normalize_spaces_around_punctuation: bool = False,
        max_length: int | None = None,
    ):
        self.lowercase = lowercase
        self.unicode_form = unicode_form
        self.collapse_whitespace = collapse_whitespace
        self.strip_punctuation = strip_punctuation
        self.strip_numbers = strip_numbers
        self.normalize_quotes = normalize_quotes
        self.normalize_dashes = normalize_dashes
        self.normalize_ellipsis = normalize_ellipsis
        self.normalize_spaces_around_punctuation = normalize_spaces_around_punctuation
        self.max_length = max_length


_QUOTE_TABLE = str.maketrans({
    "\u201c": '"',
    "\u201d": '"',
    "\u201e": '"',
    "\u201f": '"',
    "\u2018": "'",
    "\u2019": "'",
    "\u201a": "'",
    "\u201b": "'",
    "\u00ab": '"',
    "\u00bb": '"',
    "\u2039": "'",
    "\u203a": "'",
    "\u300c": "[",
    "\u300d": "]",
})

_DASH_TABLE = str.maketrans({
    "\u2013": "-",
    "\u2014": "-",
    "\u2015": "-",
    "\u2053": "-",
    "\u2212": "-",
})

_WHITESPACE = re.compile(r"\s+")
_MULTILINE_BREAKS = re.compile(r"\n{3,}")
_PUNCTUATION = re.compile(r"[^\w\s]")
_DIGITS = re.compile(r"\d+")

_JSON_INVALID_CHARS = str.maketrans({
    i: None for i in range(32) if i not in (9, 10, 13)
})
_JSON_INVALID_CHARS.update({0x7f: None})


def normalize(text: str, options: NormalizerOptions | None = None) -> str:
    opts = options or NormalizerOptions()

    if not text:
        return ""

    if opts.max_length and len(text) > opts.max_length:
        text = text[: opts.max_length]

    text = unicodedata.normalize(opts.unicode_form, text)

    if opts.lowercase:
        text = text.lower()

    if opts.normalize_quotes:
        text = text.translate(_QUOTE_TABLE)

    if opts.normalize_dashes:
        text = text.translate(_DASH_TABLE)

    if opts.normalize_ellipsis:
        text = text.replace("\u2026", "...")

    if opts.normalize_spaces_around_punctuation:
        text = re.sub(r"\s+([.,!?;:])", r"\1", text)
        text = re.sub(r"([([])\s+", r"\1", text)
        text = re.sub(r"\s+([)\]])", r"\1", text)

    if opts.strip_punctuation:
        text = _PUNCTUATION.sub("", text)

    if opts.strip_numbers:
        text = _DIGITS.sub("", text)

    if opts.collapse_whitespace:
        text = _MULTILINE_BREAKS.sub(r"\n\n", text)
        text = _WHITESPACE.sub(" ", text)
        text = text.strip()

    text = text.translate(_JSON_INVALID_CHARS)
    return text
