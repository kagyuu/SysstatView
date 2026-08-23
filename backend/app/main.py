"""FastAPI アプリの生成 (docs/P003-backend-spec.md §11).

CORS ミドルウェアを登録しない。同一オリジン構成で回避する (ADR-001)。
"""

import logging
import time

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.errors import AppError
from app.logging_setup import log_event, setup_logging
from app.routers import catalog as catalog_router
from app.routers import health as health_router
from app.routers import log_files as log_files_router


def _error_response(
    status: int, code: str, message: str, detail: str | None = None, hint: str | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "error": {"code": code, "message": message, "detail": detail, "hint": hint}
        },
    )


def create_app() -> FastAPI:
    setup_logging()
    app = FastAPI(title="SysstatView API", version="0.1.0")

    @app.middleware("http")
    async def request_log(request: Request, call_next):
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((time.perf_counter() - started) * 1000, 2)
            log_event(
                logging.ERROR,
                "http.request",
                "リクエスト処理中に未捕捉の例外が発生しました。",
                method=request.method,
                path=request.url.path,
                status=500,
                durationMs=duration_ms,
            )
            raise
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        log_event(
            logging.INFO,
            "http.request",
            "リクエストを処理しました。",
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            durationMs=duration_ms,
        )
        return response

    @app.exception_handler(AppError)
    async def handle_app_error(_: Request, exc: AppError) -> JSONResponse:
        return _error_response(
            exc.http_status, exc.code, exc.message, exc.detail, exc.hint
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        _: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return _error_response(
            400,
            "INVALID_PARAMETER",
            "リクエストパラメータが不正です。",
            detail="; ".join(
                f"{'.'.join(str(p) for p in e.get('loc', []))}: {e.get('msg', '')}"
                for e in exc.errors()
            )
            or None,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected(_: Request, exc: Exception) -> JSONResponse:
        # detail に例外の文字列表現を含めない (docs/P003-backend-spec.md §11.1)。
        # 完全な情報はログにのみ残す。
        get_logger_exc(exc)
        return _error_response(
            500, "INTERNAL_ERROR", "サーバ内部でエラーが発生しました。"
        )

    app.include_router(health_router.router)
    app.include_router(log_files_router.router)
    app.include_router(catalog_router.router)
    return app


def get_logger_exc(exc: Exception) -> None:
    logging.getLogger("sysstatview").error(
        "未捕捉の例外を INTERNAL_ERROR に変換しました。",
        exc_info=exc,
        extra={"event": "internal.error", "extra_fields": {}},
    )


app = create_app()
