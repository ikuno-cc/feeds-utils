from fastapi import APIRouter, HTTPException
from app.schemas.archive import ArchiveRequest, ArchiveResponse
from app.services.archiver import ArchiveService

router = APIRouter(tags=["Archive"])


@router.post(
    "/api/v1/archive",
    response_model=ArchiveResponse,
    summary="Submit or retrieve an archived URL from archive.ph",
    description="Submits a target URL to archive.ph (and active mirrors), resolves multi-result search pages to the single newest snapshot shortlink, and handles bot protection gracefully.",
)
async def create_archive(req: ArchiveRequest) -> ArchiveResponse:
    try:
        archive_url, domain_used, status = await ArchiveService.get_or_create_archive(
            target_url=req.url,
            preferred_domain=req.domain or "archive.ph"
        )
        return ArchiveResponse(
            original_url=req.url,
            archive_url=archive_url,
            status=status,
            domain_used=domain_used,
            error=None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post(
    "/archive",
    response_model=ArchiveResponse,
    summary="Submit or retrieve an archived URL (shortcut)",
    include_in_schema=False
)
async def create_archive_shortcut(req: ArchiveRequest) -> ArchiveResponse:
    return await create_archive(req)
