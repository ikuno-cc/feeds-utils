from typing import Any

from pydantic import BaseModel, Field, field_validator


class CleanRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Raw article text or HTML to clean")
    fix_encoding: bool = Field(True, description="Fix mojibake / wrong encoding via ftfy")
    extract_article: bool = Field(True, description="Extract main article content from HTML")
    strip_html: bool = Field(True, description="Remove all HTML tags after extraction")
    strip_scripts: bool = Field(True, description="Remove <script> tags")
    strip_styles: bool = Field(True, description="Remove <style> tags")
    decode_entities: bool = Field(True, description="Decode HTML entities")
    normalize_unicode: bool = Field(True, description="NFC unicode normalization")
    remove_urls: bool = Field(False, description="Remove URLs from text")
    remove_emails: bool = Field(False, description="Remove email addresses")
    remove_phones: bool = Field(False, description="Remove phone numbers")
    remove_emojis: bool = Field(False, description="Remove emoji characters")
    transliterate: bool = Field(False, description="Transliterate unicode to ASCII")
    remove_extra_whitespace: bool = Field(True, description="Collapse extra whitespace")
    collapse_repeated_punctuation: bool = Field(True, description="Collapse repeated !?. to max 2")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty after stripping")
        return v


class NormalizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to normalize")
    lowercase: bool = Field(True, description="Convert to lowercase")
    unicode_form: str = Field("NFC", description="Unicode normalization form: NFC, NFD, NFKC, NFKD")
    collapse_whitespace: bool = Field(True, description="Collapse all whitespace to single spaces")
    strip_punctuation: bool = Field(False, description="Remove all punctuation")
    strip_numbers: bool = Field(False, description="Remove all digits")
    normalize_quotes: bool = Field(True, description="Normalize curly quotes to straight")
    normalize_dashes: bool = Field(True, description="Normalize em/en dashes to hyphen")
    normalize_ellipsis: bool = Field(True, description="Normalize ellipsis char to three dots")
    normalize_spaces_around_punctuation: bool = Field(False, description="Remove spaces before punctuation")

    @field_validator("text")
    @classmethod
    def text_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("text must not be empty after stripping")
        return v

    @field_validator("unicode_form")
    @classmethod
    def valid_unicode_form(cls, v: str) -> str:
        allowed = {"NFC", "NFD", "NFKC", "NFKD"}
        if v.upper() not in allowed:
            raise ValueError(f"unicode_form must be one of {allowed}")
        return v.upper()


class StringToJsonRequest(BaseModel):
    text: str = Field(..., description="String to parse as JSON")
