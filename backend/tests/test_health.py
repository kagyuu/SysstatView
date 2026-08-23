"""U001-T5 / U004-T4 — GET /api/health."""
import json

from app.logging_setup import JsonFormatter
from app.readers.sa_binary import sadf_available


def test_healthが200でstatusがok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_sadf不在でも200でstatusはok(client):
    body = client.get("/api/health").json()
    assert body["sadfAvailable"] == sadf_available()
    if not sadf_available():
        assert body["sadfVersion"] is None
        assert body["status"] == "ok"


def test_件数の合計が実ファイル数と一致する(client):
    body = client.get("/api/health").json()
    assert body["readableFileCount"] + body["unreadableFileCount"] == 18


def test_sadf不在ならsar9件がreadableでsa9件がunreadable(client):
    if sadf_available():
        return
    body = client.get("/api/health").json()
    assert body["readableFileCount"] == 9
    assert body["unreadableFileCount"] == 9


def test_ログフォーマッタが1行のJSONを出す():
    import logging

    record = logging.LogRecord("x", logging.INFO, "f", 1, "改行\nあり", None, None)
    record.event = "test.event"
    line = JsonFormatter().format(record)
    assert "\n" not in line
    payload = json.loads(line)
    assert {"ts", "level", "event", "message"} <= set(payload)
