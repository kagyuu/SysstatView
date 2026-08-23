"""T001 — sar 経路の結合 (docs/P008-test-direction/T001-sar-pipeline.md)."""
import base64
import pytest

EXPECTED_GROUP_IDS = {
    "MG-CPU", "MG-PROC", "MG-SWPIO", "MG-PAGE", "MG-IO", "MG-MEM", "MG-SWAP",
    "MG-HUGE", "MG-KTBL", "MG-LOAD", "MG-TTY", "MG-DISK", "MG-NET", "MG-NETERR",
    "MG-NFSC", "MG-NFSD", "MG-SOCK", "MG-SOFTNET",
    "MG-PSI-CPU", "MG-PSI-IO", "MG-PSI-MEM",
}


def _fid(n): return base64.urlsafe_b64encode(n.encode()).decode().rstrip("=")


@pytest.fixture
def sar_items(client):
    r = client.get("/api/log-files", params={"from": "2026-08-01", "to": "2026-08-31", "perPage": 100})
    return [i for i in r.json()["items"] if i["kind"] == "sar"]


def test_全てのsarが200で返る(client, sar_items):
    assert len(sar_items) == 9
    for item in sar_items:
        r = client.get(f"/api/log-files/{item['fileId']}/metrics")
        assert r.status_code == 200, item["fileName"]


def test_sar23のグループ集合(client):
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    assert {g["groupId"] for g in body["groups"]} == EXPECTED_GROUP_IDS


def test_全ファイルでINV1が成立する(client, sar_items):
    for item in sar_items:
        body = client.get(f"/api/log-files/{item['fileId']}/metrics").json()
        for g in body["groups"]:
            n = len(g["timestamps"])
            for s in g["series"]:
                assert len(s["values"]) == n, f"{item['fileName']}/{g['groupId']}"


def test_MG_CPUのサンプル数が140件以上(client):
    """11 件や 13 件なら繰り返しヘッダでブロックが切れている。"""
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    cpu = next(g for g in body["groups"] if g["groupId"] == "MG-CPU")
    assert len(cpu["timestamps"]) >= 140


def test_MG_CPUのキー集合(client):
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    cpu = next(g for g in body["groups"] if g["groupId"] == "MG-CPU")
    assert {s["key"] for s in cpu["series"]} == {"all", "0", "1", "2"}


def test_MG_NETのキー数が20以上(client):
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    net = next(g for g in body["groups"] if g["groupId"] == "MG-NET")
    assert len({s["key"] for s in net["series"]}) >= 20


def test_Averageが混入しない(client, sar_items):
    for item in sar_items:
        body = client.get(f"/api/log-files/{item['fileId']}/metrics").json()
        assert not any("Average" in t for g in body["groups"] for t in g["timestamps"])


def test_ヘッダ情報(client):
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    assert (body["hostname"], body["cpuCount"], body["kind"], body["date"]) == (
        "www4250uj", 3, "sar", "2026-08-23"
    )


def test_カタログがメトリクスのgroupIdを包含する(client):
    cat = {g["groupId"] for g in client.get("/api/metric-catalog").json()["groups"]}
    body = client.get(f"/api/log-files/{_fid('sar23')}/metrics").json()
    assert {g["groupId"] for g in body["groups"]} <= cat
