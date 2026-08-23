"""A002 — sar のみでの運用 (docs/P009-acceptance-direction/A002-sar-only-operation.md).

この開発環境には sadf が無いため、この観点は「制約がそのまま検証条件になる」
数少ないケースであり、確実に検証できる (docs/P006-test-plan.md §6.2)。
"""

import base64

import pytest

from app.readers.sa_binary import sadf_available

pytestmark = pytest.mark.skipif(
    sadf_available(),
    reason="NOT RUN: sadf がある環境では不在条件を再現していない。"
    "PATH から sadf を外して実行すること。",
)


def _fid(name: str) -> str:
    return base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")


def test_sadfが不在であることを確認する():
    assert sadf_available() is False


def test_起動が失敗しない(client):
    """アプリが sadf 不在で起動できること。"""
    assert client.get("/api/health").status_code == 200


def test_healthがokでsadfAvailableがfalse(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["sadfAvailable"] is False
    assert body["sadfVersion"] is None
    assert body["readableFileCount"] == 9
    assert body["unreadableFileCount"] == 9


def test_一覧にsarのみが返る(client):
    body = client.get(
        "/api/log-files",
        params={"from": "2026-08-01", "to": "2026-08-31", "perPage": 100},
    ).json()
    assert body["totalItems"] == 9
    assert {i["kind"] for i in body["items"]} == {"sar"}


def test_sarのグラフデータが取得できる(client):
    r = client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    assert r.status_code == 200
    assert r.json()["groups"]


def test_saを直接指定すると503でsarへ誘導される(client):
    r = client.get(f"/api/log-files/{_fid('sa23')}/metrics")
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "SADF_UNAVAILABLE"
    assert "sar23" in (err["hint"] or "")


def test_一覧取得が5xxにならない(client):
    """sadf 不在をアプリ全体の異常として扱っていないこと。"""
    r = client.get(
        "/api/log-files", params={"from": "2026-08-01", "to": "2026-08-31"}
    )
    assert r.status_code == 200
