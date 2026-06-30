import re
import unicodedata
import html as html_mod

import ftfy
import bleach
from unidecode import unidecode
from bs4 import BeautifulSoup, Tag
from readability import Document as ReadabilityDocument
from cleantext import clean as clean_text


_INVISIBLE_CHARS = re.compile(
    "[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\x81\x8d\x8f\x90\x9d\xa0\xad"
    "\u034f\u061c\u115f\u1160\u17b4\u17b5\u180e\u2000-\u200f"
    "\u2028-\u202f\u205f\u2060-\u2064\u2066-\u206f\u3000\u2800"
    "\U000e0001\U000e0020-\U000e007f\U000e0100-\U000e01ef"
    "\ufe00-\ufe0f\ufff0-\ufff8]"
)

_URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
_PHONE_PATTERN = re.compile(r"\+?\d[\d\s().-]{7,}\d")
_REPEATED_PUNCTUATION = re.compile(r"([!?.]){3,}")
_MULTILINE_BREAKS = re.compile(r"\n{3,}")
_MULTISPACE = re.compile(r"[ \t]{2,}")
_SCRIPT_STYLE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.DOTALL | re.IGNORECASE)

_JSON_INVALID_CHARS = str.maketrans({
    i: None for i in range(32) if i not in (9, 10, 13)
})
_JSON_INVALID_CHARS.update({0x7f: None})
_JSON_SAFE = _JSON_INVALID_CHARS


def _extract_article_html(raw_html: str) -> str:
    doc = ReadabilityDocument(raw_html)
    return doc.summary()


def _soup_clean(html_content: str, strip_scripts: bool = True, strip_styles: bool = True) -> str:
    soup = BeautifulSoup(html_content, "lxml")

    if strip_scripts:
        for tag in soup.find_all("script"):
            tag.decompose()
    if strip_styles:
        for tag in soup.find_all("style"):
            tag.decompose()

    for tag in soup.find_all(["nav", "footer", "header", "aside", "noscript", "iframe"]):
        tag.decompose()

    for tag in soup.find_all(True):
        if isinstance(tag, Tag):
            attrs_to_keep = {"href", "src", "alt", "title", "class"}
            for attr in list(tag.attrs):
                if attr not in attrs_to_keep:
                    del tag[attr]

    return str(soup)


def _bleach_sanitize(html_content: str) -> str:
    allowed_tags = {
        "p", "br", "b", "i", "u", "em", "strong", "a", "ul", "ol",
        "li", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote",
        "pre", "code", "hr", "sub", "sup", "span", "div",
    }
    allowed_attrs = {"a": ["href", "title", "rel"], "img": ["src", "alt"]}
    return bleach.clean(
        html_content,
        tags=allowed_tags,
        attributes=allowed_attrs,
        strip=True,
    )


class CleanerOptions:
    def __init__(
        self,
        fix_encoding: bool = True,
        extract_article: bool = True,
        strip_html: bool = True,
        strip_scripts: bool = True,
        strip_styles: bool = True,
        decode_entities: bool = True,
        normalize_unicode: bool = True,
        remove_urls: bool = False,
        remove_emails: bool = False,
        remove_phones: bool = False,
        remove_emojis: bool = False,
        transliterate: bool = False,
        remove_extra_whitespace: bool = True,
        collapse_repeated_punctuation: bool = True,
        max_length: int | None = None,
    ):
        self.fix_encoding = fix_encoding
        self.extract_article = extract_article
        self.strip_html = strip_html
        self.strip_scripts = strip_scripts
        self.strip_styles = strip_styles
        self.decode_entities = decode_entities
        self.normalize_unicode = normalize_unicode
        self.remove_urls = remove_urls
        self.remove_emails = remove_emails
        self.remove_phones = remove_phones
        self.remove_emojis = remove_emojis
        self.transliterate = transliterate
        self.remove_extra_whitespace = remove_extra_whitespace
        self.collapse_repeated_punctuation = collapse_repeated_punctuation
        self.max_length = max_length


def clean(text: str, options: CleanerOptions | None = None) -> str:
    opts = options or CleanerOptions()

    if not text:
        return ""

    if opts.max_length and len(text) > opts.max_length:
        text = text[: opts.max_length]

    if opts.fix_encoding:
        text = ftfy.fix_text(text)

    if opts.normalize_unicode:
        text = unicodedata.normalize("NFC", text)

    if opts.transliterate:
        text = unidecode(text)

    has_html = bool(BeautifulSoup(text, "html.parser").find())

    if has_html:
        if opts.extract_article:
            try:
                text = _extract_article_html(text)
            except Exception:
                pass
        if opts.strip_scripts or opts.strip_styles:
            text = _SCRIPT_STYLE.sub("", text)
        text = _soup_clean(text, strip_scripts=False, strip_styles=False)

        if opts.strip_html:
            text = bleach.clean(text, tags=[], attributes={}, strip=True)
        else:
            text = _bleach_sanitize(text)

    if opts.decode_entities and (opts.strip_html or not has_html):
        text = html_mod.unescape(text)

    if opts.remove_urls:
        text = _URL_PATTERN.sub("", text)
    if opts.remove_emails:
        text = _EMAIL_PATTERN.sub("", text)
    if opts.remove_phones:
        text = _PHONE_PATTERN.sub("", text)

    text = _INVISIBLE_CHARS.sub("", text)

    if opts.remove_emojis:
        text = clean_text(text, no_emoji=True)

    if opts.collapse_repeated_punctuation:
        text = _REPEATED_PUNCTUATION.sub(r"\1\1", text)

    if opts.remove_extra_whitespace:
        text = _MULTILINE_BREAKS.sub(r"\n\n", text)
        text = _MULTISPACE.sub(" ", text)
        text = text.strip()

    text = text.translate(_JSON_SAFE)
    return text


clean.__doc__ = """Clean article text by fixing encoding, stripping HTML, removing unwanted content.

Args:
    text: Raw article text or HTML.
    options: Cleaning options (defaults to sensible defaults).

Returns:
    Cleaned text string.
"""
