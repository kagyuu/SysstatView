"""T004 — エラー系とパストラバーサル (docs/P008-test-direction/T004-error-and-traversal.md)."""

import base64

import pytest

from app.readers.sa_binary import sadf_available


def _fid(name: str) -> str:
    return base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")


@pytest.mark.parametrize(
    "params",
    [
        {"to": "2026-08-31"},
        {"from": "2026-08-01"},
        {"from": "2026-13-01", "to": "2026-08-31"},
        {"from": "2026-08-31", "to": "2026-08-01"},
        {"from": "2026-08-01", "to": "2026-08-31", "page": 0},
        {"from": "2026-08-01", "to": "2026-08-31", "perPage": 101},
        {"from": "2026-08-01", "to": "2026-08-31", "perPage": 0},
    ],
)
def test_パラメータ異常は400(client, params):
    r = client.get("/api/log-files", params=params)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_PARAMETER"


@pytest.mark.parametrize(
    "raw",
    [
        "notbase64!!",
        _fid("../../etc/passwd"),
        _fid("/etc/passwd"),
        _fid("README.md"),
        _fid("sa99"),
        _fid("sa1"),
        _fid("sa123"),
    ],
)
def test_不正なfileIdはすべて404(client, raw):
    """パストラバーサル系が 404 以外を返した場合は重大な欠陥である。"""
    r = client.get(f"/api/log-files/{raw}/metrics")
    assert r.status_code == 404, f"{raw} が 404 以外を返した"
    assert r.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_エラー応答の形式(client):
    body = client.get(f"/api/log-files/{_fid('sa99')}/metrics").json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message", "detail", "hint"}


def test_メッセージが日本語(client):
    msg = client.get(f"/api/log-files/{_fid('sa99')}/metrics").json()["error"]["message"]
    assert any(
        "぀" <= ch <= "ヿ" or "一" <= ch <= "鿿" for ch in msg
    ), msg


@pytest.mark.skipif(sadf_available(), reason="sadf がある環境では 200 になる")
def test_sadf不在でsaは503かつhintに同日のsarが載る(client):
    r = client.get(f"/api/log-files/{_fid('sa23')}/metrics")
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "SADF_UNAVAILABLE"
    assert "sar23" in (err["hint"] or "")
