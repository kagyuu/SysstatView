"""U001-T2"""
import pytest
from fastapi import APIRouter
from fastapi.testclient import TestClient

from app.errors import (
    AppError,
    FileNotFoundAppError,
    InvalidParameterError,
    ParseFailedError,
    SadfFailedError,
    SadfUnavailableError,
    UnsupportedFileError,
)
from app.main import create_app


@pytest.mark.parametrize(
    "cls,code,status",
    [
        (InvalidParameterError, "INVALID_PARAMETER", 400),
        (FileNotFoundAppError, "FILE_NOT_FOUND", 404),
        (UnsupportedFileError, "UNSUPPORTED_FILE", 422),
        (ParseFailedError, "PARSE_FAILED", 422),
        (SadfUnavailableError, "SADF_UNAVAILABLE", 503),
        (SadfFailedError, "SADF_FAILED", 502),
    ],
)
def test_例外クラスのコードとHTTPステータス(cls, code, status):
    assert cls.code == code
    assert cls.http_status == status
    assert issubclass(cls, AppError)


def _app_with(route_fn):
    app = create_app()
    router = APIRouter()
    router.add_api_route("/_t", route_fn, methods=["GET"])
    app.include_router(router)
    return TestClient(app, raise_server_exceptions=False)


def test_AppErrorが規定の形式に変換される():
    def boom():
        raise SadfFailedError("失敗しました。", detail="stderr text", hint="代替案")

    r = _app_with(boom).get("/_t")
    assert r.status_code == 502
    body = r.json()["error"]
    assert body == {
        "code": "SADF_FAILED",
        "message": "失敗しました。",
        "detail": "stderr text",
        "hint": "代替案",
    }


def test_未捕捉例外は500になりdetailに内部情報を含めない():
    def boom():
        raise RuntimeError("秘密の内部メッセージ")

    r = _app_with(boom).get("/_t")
    assert r.status_code == 500
    body = r.json()["error"]
    assert body["code"] == "INTERNAL_ERROR"
    assert body["detail"] is None
    assert "秘密の内部メッセージ" not in r.text
