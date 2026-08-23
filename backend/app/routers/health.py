"""GET /api/health (docs/P002-frontend-spec.md §5.5).

sadf が無くても status は "ok" を返す。sar のみで運用する構成を正常とみなすため
(REQ-N-015)。
"""

from fastapi import APIRouter

from app.config import get_settings
from app.models import HealthResponse
from app.readers.sa_binary import sadf_available, sadf_version
from app.services.catalog_service import get_catalog_service

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/health", response_model=HealthResponse)
def get_health() -> HealthResponse:
    settings = get_settings()
    available = sadf_available()
    readable, unreadable = get_catalog_service().counts(settings.log_dir)
    return HealthResponse(
        status="ok",
        logDir=settings.log_dir_str,
        sadfAvailable=available,
        sadfVersion=sadf_version() if available else None,
        readableFileCount=readable,
        unreadableFileCount=unreadable,
    )
