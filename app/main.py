from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.clean import router as clean_router
from app.api.routes.fact_check import router as fact_check_router
from app.api.routes.archive import router as archive_router
from app.core.config import settings

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(clean_router)
app.include_router(fact_check_router)
app.include_router(archive_router)



@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": settings.app_version}
