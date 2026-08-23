"""T006 — 構造化ログ (docs/P008-test-direction/T006-structured-log.md)."""

import base64
import io
import json
import logging

import pytest

from app.logging_setup import get_logger
from app.readers.sa_binary import sadf_available


def _fid(name: str) -> str:
    return base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")


@pytest.fixture
def log_buffer():
    """ロガーの出力先を差し替えて捕捉する。"""
    logger = get_logger()
    handlers = [h for h in logger.handlers if isinstance(h, logging.StreamHandler)]
    originals = [h.stream for h in handlers]
    buf = io.StringIO()
    for handler in handlers:
        handler.stream = buf
    yield buf
    for handler, stream in zip(handlers, originals):
        handler.stream = stream


def _records(buf: io.StringIO) -> list[dict]:
    return [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]


def test_各行が単独でJSONとして解釈できる(client, log_buffer):
    client.get("/api/health")
    client.get("/api/log-files", params={"from": "2026-08-01", "to": "2026-08-31"})
    # json.loads が例外を投げなければ、複数行にまたがるレコードが無いことになる。
    recs = _records(log_buffer)
    assert recs, "ログが 1 件も出ていない"


def test_必須フィールドが揃っている(client, log_buffer):
    client.get("/api/health")
    for rec in _records(log_buffer):
        assert {"ts", "level", "event", "message"} <= set(rec), rec


def test_リクエストログの内容(client, log_buffer):
    client.get("/api/health")
    reqs = [r for r in _records(log_buffer) if r["event"] == "http.request"]
    assert reqs
    rec = reqs[-1]
    assert rec["method"] == "GET"
    assert rec["path"] == "/api/health"
    assert rec["status"] == 200
    assert isinstance(rec["durationMs"], (int, float))


def test_404もリクエストログに記録される(client, log_buffer):
    client.get(f"/api/log-files/{_fid('sa99')}/metrics")
    statuses = [
        r.get("status") for r in _records(log_buffer) if r["event"] == "http.request"
    ]
    assert 404 in statuses


def test_読み取り失敗がreaderfailedとして記録される(client, log_buffer):
    client.get(
        "/api/log-files",
        params={"from": "2026-08-01", "to": "2026-08-31", "perPage": 100},
    )
    events = {r["event"] for r in _records(log_buffer)}
    if not sadf_available():
        # sadf が無い環境では sa 9 件が読めず reader.failed が出る。
        assert "reader.failed" in events


def test_readerfailedにファイル名と理由が載る(client, log_buffer):
    client.get(
        "/api/log-files",
        params={"from": "2026-08-01", "to": "2026-08-31", "perPage": 100},
    )
    failed = [r for r in _records(log_buffer) if r["event"] == "reader.failed"]
    if failed:
        assert "fileName" in failed[0]
        assert "reason" in failed[0]
