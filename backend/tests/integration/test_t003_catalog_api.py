"""T003 — カタログAPIの結合 (docs/P008-test-direction/T003-catalog-api.md)."""

import shutil

from app.readers.sa_binary import sadf_available
from tests.conftest import make_client

# sadf が無い環境では sa がすべて unreadable になり、一覧は sar 9 件のみになる。
EXPECTED_TOTAL = 18 if sadf_available() else 9
ALL = {"from": "2026-08-01", "to": "2026-08-31", "perPage": 100}


def test_期間全体の件数と種別(client):
    body = client.get("/api/log-files", params=ALL).json()
    assert body["totalItems"] == EXPECTED_TOTAL
    kinds = {i["kind"] for i in body["items"]}
    assert kinds == ({"sa", "sar"} if sadf_available() else {"sar"})


def test_並び順が日付昇順で同一日はsaが先(client):
    items = client.get("/api/log-files", params=ALL).json()["items"]
    keys = [(i["date"], 0 if i["kind"] == "sa" else 1, i["fileName"]) for i in items]
    assert keys == sorted(keys)


def test_単日指定で当日のみ返る(client):
    body = client.get(
        "/api/log-files", params={"from": "2026-08-23", "to": "2026-08-23"}
    ).json()
    assert {i["fileName"] for i in body["items"]} >= {"sar23"}
    assert all(i["date"] == "2026-08-23" for i in body["items"])


def test_ページ境界(copied_log_dir, monkeypatch):
    """1 ページ 10 件に対して 2 ページ目が生じる規模を tmp 上に作る。

    実データディレクトリは書き換えない (docs/P006-test-plan.md §5.2)。
    """
    src = copied_log_dir / "sar23"
    for day in range(1, 15):
        dest = copied_log_dir / f"sar{day:02d}"
        if not dest.exists():
            shutil.copy2(src, dest)
    c = make_client(copied_log_dir, monkeypatch)
    body = c.get(
        "/api/log-files", params={"from": "2026-08-01", "to": "2026-08-31"}
    ).json()
    assert body["totalPages"] >= 2
    page2 = c.get(
        "/api/log-files",
        params={"from": "2026-08-01", "to": "2026-08-31", "page": 2},
    ).json()
    assert len(page2["items"]) == min(10, body["totalItems"] - 10)


def test_0件のとき総ページ数が0(client):
    zero = client.get(
        "/api/log-files", params={"from": "2020-01-01", "to": "2020-01-02"}
    ).json()
    assert zero["totalItems"] == 0
    assert zero["totalPages"] == 0
    assert zero["items"] == []


def test_総ページ超過は200で空配列(client):
    over = client.get("/api/log-files", params={**ALL, "page": 99})
    assert over.status_code == 200
    assert over.json()["items"] == []


def test_応答フィールドがcamelCase(client):
    item = client.get("/api/log-files", params=ALL).json()["items"][0]
    assert set(item) == {
        "fileId",
        "fileName",
        "kind",
        "date",
        "sizeBytes",
        "hostname",
    }


def test_healthの件数と一覧が整合する(client):
    health = client.get("/api/health").json()
    listing = client.get(
        "/api/log-files",
        params={"from": "1970-01-01", "to": "2999-12-31", "perPage": 100},
    ).json()
    assert health["readableFileCount"] == listing["totalItems"]
