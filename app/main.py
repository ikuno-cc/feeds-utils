from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes.clean import router as clean_router
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


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": settings.app_name, "version": settings.app_version}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok", "version": settings.app_version}
