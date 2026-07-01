from fastapi import APIRouter, HTTPException

from app.schemas.fact_check import ClaimInput, FactCheckRequest
from app.services.fact_checker import fact_check

router = APIRouter(prefix="/api/v1")


@router.post(
    "/fact-check",
    response_model=list[ClaimInput],
    summary="Fact-check claims against articles",
    description="Verify a list of claims against provided articles using hybrid retrieval (keyword BM25 + numeric overlap). Returns only the claims that are supported by the articles.",
)
def fact_check_endpoint(req: FactCheckRequest):
    try:
        claims_dicts = [c.model_dump() for c in req.claims]
        articles_dicts = [a.model_dump() for a in req.articles]

        verified = fact_check(
            claims=claims_dicts,
            articles=articles_dicts,
            threshold=req.threshold,
        )

        return verified
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
