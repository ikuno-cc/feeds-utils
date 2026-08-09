from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, HttpUrl


class JsonFormat(BaseModel):
    type: str = Field("json", description="Format type, must be 'json'")
    schema_: Optional[Dict[str, Any]] = Field(
        None,
        alias="schema",
        description="JSON Schema describing the desired output structure",
    )

    model_config = {"populate_by_name": True}


class ScrapeRequest(BaseModel):
    url: str = Field(..., description="The URL to scrape")
    formats: List[JsonFormat] = Field(
        default_factory=list,
        description="List of output formats with optional schemas",
    )


class ScrapeResult(BaseModel):
    type: str = Field(..., description="Format type, e.g. 'json'")
    data: Optional[Dict[str, Any]] = Field(None, description="Extracted structured data")
    error: Optional[str] = Field(None, description="Error message if extraction failed")


class ScrapeResponse(BaseModel):
    url: str = Field(..., description="The URL that was scraped")
    status: str = Field(..., description="'success' or 'error'")
    results: List[ScrapeResult] = Field(default_factory=list, description="Extraction results per format")
    error: Optional[str] = Field(None, description="Top-level error if scraping itself failed")
