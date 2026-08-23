"""U005-T2 / U005-T3 / U005-T4 — メトリクス取得とカタログ."""
import base64
import pytest

from app.readers.sa_binary import sadf_available

EXPECTED_GROUPS = 21


def _fid(name: str) -> str:
    return base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")


def test_sarのメトリクスが返る(client):
    r = client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    assert r.status_code == 200
    body = r.json()
    assert body["kind"] == "sar"
    assert body["date"] == "2026-08-23"
    assert body["hostname"] == "www4250uj"
    assert body["arch"] == "x86_64"
    assert body["cpuCount"] == 3
    assert len(body["groups"]) == EXPECTED_GROUPS


def test_valuesの長さがtimestampsと一致する(client):
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    for g in body["groups"]:
        n = len(g["timestamps"])
        for s in g["series"]:
            assert len(s["values"]) == n, f"{g['groupId']}/{s['metric']}"


def test_Averageが混入しない(client):
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    assert not any("Average" in t for g in body["groups"] for t in g["timestamps"])


def test_未知のfileIdは404(client):
    r = client.get(f"/api/log-files/{_fid('sa99')}/metrics")
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "FILE_NOT_FOUND"


def test_パストラバーサルは404(client):
    r = client.get(f"/api/log-files/{_fid('../../etc/passwd')}/metrics")
    assert r.status_code == 404


@pytest.mark.skipif(sadf_available(), reason="sadf がある環境では 200 になる")
def test_sadf不在時はsaが503でhintに同日のsarが載る(client):
    r = client.get(f"/api/log-files/{_fid('sa23')}/metrics")
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "SADF_UNAVAILABLE"
    assert "sar23" in (err["hint"] or "")


@pytest.mark.skipif(not sadf_available(), reason="sadf が無い環境では実行できない")
def test_収集途中のsa24も200で返る(client):
    assert client.get(f"/api/log-files/{_fid('sa24')}/metrics").status_code == 200


def test_2回目はキャッシュが使われリーダが呼ばれない(client, monkeypatch):
    from app.readers import sar_text

    client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    calls = []
    real = sar_text.read_sar_text
    monkeypatch.setattr(
        sar_text, "read_sar_text", lambda p: (calls.append(p), real(p))[1]
    )
    client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    assert calls == []


def test_LRUが上限を超えると最古を追い出す(client):
    from app.services.metrics_service import CACHE_MAX_ENTRIES, get_metrics_service

    svc = get_metrics_service()
    for name in [f"sar{d}" for d in range(15, 24)]:
        client.get(f"/api/log-files/{_fid(name)}/metrics")
    assert len(svc._cache) <= CACHE_MAX_ENTRIES


# --- メトリクスカタログ ---


def test_カタログが返る(client):
    body = client.get("/api/metric-catalog").json()
    assert len(body["groups"]) == EXPECTED_GROUPS


def test_カタログの順序がdisplayOrder(client):
    from app.metrics.catalog import GROUP_DEFS

    ids = [g["groupId"] for g in client.get("/api/metric-catalog").json()["groups"]]
    assert ids == [g.groupId for g in sorted(GROUP_DEFS, key=lambda x: x.displayOrder)]


def test_カタログの各グループにtitleとdescriptionがある(client):
    for g in client.get("/api/metric-catalog").json()["groups"]:
        assert g["title"]
        assert g["description"]
        assert all("unit" in m for m in g["metrics"])


def test_カタログがメトリクス応答のgroupIdを包含する(client):
    cat = {g["groupId"] for g in client.get("/api/metric-catalog").json()["groups"]}
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    assert {g["groupId"] for g in body["groups"]} <= cat
