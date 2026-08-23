"""U004-T3 — GET /api/log-files."""
import pytest

from app.readers.sa_binary import sadf_available

# sadf が無い環境では sa がすべて unreadable になるため期待件数が変わる。
EXPECTED_TOTAL = 18 if sadf_available() else 9
ALL = {"from": "2026-08-01", "to": "2026-08-31", "perPage": 100}


def test_期間内の件数(client):
    r = client.get("/api/log-files", params=ALL)
    assert r.status_code == 200
    assert r.json()["totalItems"] == EXPECTED_TOTAL


def test_sadfがあればsaとsarの両方が返る(client):
    kinds = {i["kind"] for i in client.get("/api/log-files", params=ALL).json()["items"]}
    assert kinds == ({"sa", "sar"} if sadf_available() else {"sar"})


def test_並び順が日付昇順で同一日はsaが先(client):
    items = client.get("/api/log-files", params=ALL).json()["items"]
    keys = [(i["date"], 0 if i["kind"] == "sa" else 1, i["fileName"]) for i in items]
    assert keys == sorted(keys)


def test_境界日が含まれる(client):
    r = client.get("/api/log-files", params={"from": "2026-08-23", "to": "2026-08-23"})
    names = {i["fileName"] for i in r.json()["items"]}
    assert "sar23" in names


def test_1ページ10件でページ分割される(client):
    r = client.get("/api/log-files", params={"from": "2026-08-01", "to": "2026-08-31"})
    body = r.json()
    assert body["perPage"] == 10
    assert body["totalItems"] == EXPECTED_TOTAL
    assert body["totalPages"] == (2 if EXPECTED_TOTAL > 10 else 1)
    assert len(body["items"]) == min(10, EXPECTED_TOTAL)


def test_2ページ目の件数(client):
    body = client.get(
        "/api/log-files", params={"from": "2026-08-01", "to": "2026-08-31", "page": 2}
    ).json()
    assert len(body["items"]) == max(0, EXPECTED_TOTAL - 10)


def test_0件のときtotalPagesは0(client):
    body = client.get(
        "/api/log-files", params={"from": "2020-01-01", "to": "2020-01-02"}
    ).json()
    assert body["totalItems"] == 0
    assert body["totalPages"] == 0
    assert body["items"] == []


def test_総ページ超過は200で空配列(client):
    r = client.get("/api/log-files", params={**ALL, "page": 99})
    assert r.status_code == 200
    assert r.json()["items"] == []


def test_応答フィールドがcamelCase(client):
    item = client.get("/api/log-files", params=ALL).json()["items"][0]
    assert set(item) == {"fileId", "fileName", "kind", "date", "sizeBytes", "hostname"}


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
def test_不正なパラメータは400(client, params):
    r = client.get("/api/log-files", params=params)
    assert r.status_code == 400
    assert r.json()["error"]["code"] == "INVALID_PARAMETER"
