"""GET /api/log-files, GET /api/log-files/{fileId}/metrics
(docs/P002-frontend-spec.md §5.2, §5.3).
"""

from fastapi import APIRouter, Query

from app.config import get_settings
from app.models import LogFileListResponse, MetricsResponse
from app.services.catalog_service import (
    get_catalog_service,
    parse_date_param,
    validate_paging,
)
from app.errors import InvalidParameterError
from app.services.metrics_service import get_metrics_service

router = APIRouter(prefix="/api", tags=["log-files"])


@router.get("/log-files", response_model=LogFileListResponse)
def list_log_files(
    from_: str = Query(..., alias="from"),
    to: str = Query(...),
    page: int = Query(1),
    perPage: int = Query(10),
) -> LogFileListResponse:
    date_from = parse_date_param(from_, "from")
    date_to = parse_date_param(to, "to")
    if date_from > date_to:
        raise InvalidParameterError(
            "開始日は終了日以前の日付を指定してください。",
            detail=f"from={from_}, to={to}",
        )
    validate_paging(page, perPage)

    settings = get_settings()
    items, total_items, total_pages = get_catalog_service().list_page(
        settings.log_dir, date_from, date_to, page, perPage
    )
    return LogFileListResponse(
        page=page,
        perPage=perPage,
        totalItems=total_items,
        totalPages=total_pages,
        items=items,
    )


@router.get("/log-files/{fileId}/metrics", response_model=MetricsResponse)
def get_log_file_metrics(fileId: str) -> MetricsResponse:
    settings = get_settings()
    return get_metrics_service().get_metrics(
        fileId, settings.log_dir, get_catalog_service()
    )
