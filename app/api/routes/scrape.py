from fastapi import APIRouter, HTTPException

from app.schemas.scrape import ScrapeRequest, ScrapeResponse, ScrapeResult
from app.services.scraper import ScraperService

router = APIRouter(tags=["Scrape"])


@router.post(
    "/api/v1/scrape",
    response_model=ScrapeResponse,
    summary="Scrape a URL and extract structured data",
    description=(
        "Fetches the target URL using a headless browser (Playwright stealth) with "
        "curl_cffi and httpx as fallbacks, then extracts structured fields from the page "
        "HTML (JSON-LD, Open Graph, meta tags, article body) according to the provided "
        "JSON Schema. Preserves raw HTML in content including tables, images, and RTL wrappers."
    ),
)
async def scrape_url(req: ScrapeRequest) -> ScrapeResponse:
    results: list[ScrapeResult] = []

    if not req.formats:
        # No formats specified — do a default extraction
        try:
            data = await ScraperService.scrape(req.url, schema=None)
            results.append(ScrapeResult(type="json", data=data))
        except Exception as exc:
            return ScrapeResponse(url=req.url, status="error", results=[], error=str(exc))
    else:
        for fmt in req.formats:
            if fmt.type.lower() != "json":
                results.append(
                    ScrapeResult(
                        type=fmt.type,
                        data=None,
                        error=f"Unsupported format type: {fmt.type!r}. Only 'json' is supported.",
                    )
                )
                continue
            try:
                data = await ScraperService.scrape(req.url, schema=fmt.schema_)
                results.append(ScrapeResult(type="json", data=data))
            except Exception as exc:
                results.append(ScrapeResult(type="json", data=None, error=str(exc)))

    overall_status = "error" if all(r.error for r in results) else "success"
    return ScrapeResponse(url=req.url, status=overall_status, results=results)


@router.post(
    "/scrape",
    response_model=ScrapeResponse,
    summary="Scrape a URL (shortcut)",
    include_in_schema=False,
)
async def scrape_url_shortcut(req: ScrapeRequest) -> ScrapeResponse:
    return await scrape_url(req)
