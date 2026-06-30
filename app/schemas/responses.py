from typing import Any

from pydantic import BaseModel, Field


class CleanResponse(BaseModel):
    cleaned: str = Field(..., description="The cleaned article text")
    original_length: int = Field(..., description="Length of the original input")
    cleaned_length: int = Field(..., description="Length of the cleaned output")
    chars_removed: int = Field(..., description="Number of characters removed during cleaning")


class NormalizeResponse(BaseModel):
    normalized: str = Field(..., description="The normalized text")
    original_length: int = Field(..., description="Length of the original input")
    normalized_length: int = Field(..., description="Length of the normalized output")


class StringToJsonResponse(BaseModel):
    original: str = Field(..., description="The original input string")
    parsed: Any = Field(None, description="Parsed JSON value if valid")
    is_valid: bool = Field(..., description="Whether the string is valid JSON")
    error: str | None = Field(None, description="Error message if invalid")


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
