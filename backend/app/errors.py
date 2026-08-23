"""ドメイン例外 (docs/P003-backend-spec.md §11.1).

リーダ層・サービス層は本モジュールの例外のみを投げる。HTTPException を投げない。
HTTP への変換は app/main.py の単一ハンドラが行う。
"""


class AppError(Exception):
    """アプリケーション例外の基底。"""

    code: str = "INTERNAL_ERROR"
    http_status: int = 500

    def __init__(
        self,
        message: str,
        *,
        detail: str | None = None,
        hint: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
        self.hint = hint


class InvalidParameterError(AppError):
    code = "INVALID_PARAMETER"
    http_status = 400


class FileNotFoundAppError(AppError):
    code = "FILE_NOT_FOUND"
    http_status = 404


class UnsupportedFileError(AppError):
    code = "UNSUPPORTED_FILE"
    http_status = 422


class ParseFailedError(AppError):
    code = "PARSE_FAILED"
    http_status = 422


class SadfUnavailableError(AppError):
    code = "SADF_UNAVAILABLE"
    http_status = 503


class SadfFailedError(AppError):
    code = "SADF_FAILED"
    http_status = 502


class InternalError(AppError):
    """正規化の不変条件違反など、内部の欠陥を示す。

    detail に内部情報を載せない (docs/P003-backend-spec.md §11.1)。
    """

    code = "INTERNAL_ERROR"
    http_status = 500
