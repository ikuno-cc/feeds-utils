from typing import Optional
from pydantic import BaseModel, Field, field_validator


class ArchiveRequest(BaseModel):
    url: str = Field(..., min_length=1, description="URL of the web page to submit or retrieve from archive")
    domain: Optional[str] = Field("archive.ph", description="Preferred archive domain (archive.ph, archive.today, archive.is, etc.)")

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("URL must not be empty")
        if not (v.startswith("http://") or v.startswith("https://")):
            raise ValueError("URL must start with http:// or https://")
        return v


class ArchiveResponse(BaseModel):
    original_url: str = Field(..., description="The original target URL requested")
    archive_url: Optional[str] = Field(None, description="The resulting single shortlink URL (e.g. https://archive.ph/H6GcX)")
    status: str = Field(..., description="Status of the archive operation (success, wayback_fallback, or captcha_required)")
    domain_used: str = Field(..., description="The archive domain that satisfied the request")
    error: Optional[str] = Field(None, description="Error message if any occurred")
