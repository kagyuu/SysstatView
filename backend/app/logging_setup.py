"""標準出力への構造化 (JSON) ログ (docs/P003-backend-spec.md §12).

1 行 1 レコード。必須フィールドは ts / level / event / message。
追加フィールドは logger.info(..., extra={"extra_fields": {...}}) で載せる。
"""

import json
import logging
import sys
from datetime import datetime, timezone

LOGGER_NAME = "sysstatview"

# LogRecord の標準属性。extra で渡された独自フィールドを見分けるために使う。
_STANDARD_ATTRS = frozenset(
    vars(logging.LogRecord("", 0, "", 0, "", None, None)).keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, object] = {
            "ts": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.name),
            "message": record.getMessage(),
        }
        extra = getattr(record, "extra_fields", None)
        if isinstance(extra, dict):
            payload.update(extra)
        for key, value in vars(record).items():
            if key not in _STANDARD_ATTRS and key not in ("event", "extra_fields"):
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # ensure_ascii=False で日本語をそのまま出す。改行は JSON 内でエスケープされるため
        # 1 レコードが必ず 1 行に収まる。
        return json.dumps(payload, ensure_ascii=False, default=str)


def setup_logging(level: int = logging.INFO) -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    # 再入時にハンドラが二重登録されないようにする (テストで create_app を複数回呼ぶため)。
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger


def get_logger() -> logging.Logger:
    logger = logging.getLogger(LOGGER_NAME)
    if not logger.handlers:
        setup_logging()
    return logger


def log_event(level: int, event: str, message: str, **fields: object) -> None:
    get_logger().log(level, message, extra={"event": event, "extra_fields": fields})
