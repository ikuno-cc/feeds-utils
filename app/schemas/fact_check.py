from pydantic import BaseModel, Field


class ClaimInput(BaseModel):
    claim: str = Field(..., description="The claim text to verify")
    subject: str = Field("", description="Subject of the claim")
    predicate: str = Field("", description="Predicate of the claim")
    value: float | None = Field(None, description="Numeric value in the claim")
    unit: str = Field("", description="Unit of the numeric value")
    period: str = Field("", description="Time period relevant to the claim")
    basis: str = Field("", description="Basis or context of the claim")
    source_sentence: str = Field("", description="Original sentence the claim was derived from")
    source_id: str = Field("", description="Identifier of the source article")


class ArticleInput(BaseModel):
    id: list[str] = Field(default_factory=list, description="Article identifiers")
    clean_text: list[str] = Field(default_factory=list, description="Cleaned article text paragraphs")


class FactCheckRequest(BaseModel):
    claims: list[ClaimInput] = Field(..., min_length=1, description="List of claims to verify")
    articles: list[ArticleInput] = Field(..., min_length=1, description="List of articles to check against")
    threshold: float = Field(0.3, description="Minimum hybrid score to consider a claim verified", ge=0.0, le=1.0)
