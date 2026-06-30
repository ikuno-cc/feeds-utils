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


class ErrorResponse(BaseModel):
    detail: str = Field(..., description="Error message")
