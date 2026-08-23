"""T002 — 2 経路の一致 (観点A)。

sadf が無い環境では実行できない。その場合は NOT RUN として記録し、
合格として扱わない (docs/P008-test-direction/T002-dual-path-equivalence.md)。
"""
import base64
import pytest

from app.readers.sa_binary import sadf_available

pytestmark = pytest.mark.skipif(
    not sadf_available(),
    reason="NOT RUN: この環境に sadf が無く導入もできないため実行できない "
           "(docs/ArchitectureHandbook.md §9-1)。合格として扱わないこと。",
)

TOLERANCE = 0.01


def _fid(n): return base64.urlsafe_b64encode(n.encode()).decode().rstrip("=")


@pytest.mark.parametrize("day", [f"{d:02d}" for d in range(16, 24)])
def test_同一日のsaとsarの結果が一致する(client, day):
    sa = client.get(f"/api/log-files/{_fid('sa' + day)}/metrics")
    sar = client.get(f"/api/log-files/{_fid('sar' + day)}/metrics")
    assert sa.status_code == 200 and sar.status_code == 200
    a, b = sa.json(), sar.json()

    assert a["date"] == b["date"]
    assert (a["hostname"], a["kernel"], a["arch"], a["cpuCount"]) == (
        b["hostname"], b["kernel"], b["arch"], b["cpuCount"]
    )

    ga = {g["groupId"]: g for g in a["groups"]}
    gb = {g["groupId"]: g for g in b["groups"]}
    assert set(ga) == set(gb), f"グループ集合が不一致: {set(ga) ^ set(gb)}"

    for gid in ga:
        assert ga[gid]["keyLabel"] == gb[gid]["keyLabel"], gid
        assert ga[gid]["timestamps"] == gb[gid]["timestamps"], gid
        sa_map = {(s["key"], s["metric"]): s["values"] for s in ga[gid]["series"]}
        sar_map = {(s["key"], s["metric"]): s["values"] for s in gb[gid]["series"]}
        assert set(sa_map) == set(sar_map), f"{gid}: 系列集合が不一致"
        for key in sa_map:
            for i, (x, y) in enumerate(zip(sa_map[key], sar_map[key])):
                if x is None or y is None:
                    assert x == y, f"{gid}/{key}[{i}]: 片方だけ None"
                else:
                    assert abs(x - y) <= TOLERANCE, f"{gid}/{key}[{i}]: {x} != {y}"
