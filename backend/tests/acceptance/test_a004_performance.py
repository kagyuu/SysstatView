"""A004 — 性能 (docs/P009-acceptance-direction/A004-performance.md).

ブラウザ描画時間 (SC-02 の最初のグラフ) は計測手段が無いため NOT RUN とする。
API の応答時間のみを測定する。
"""

import base64
import shutil
import statistics
import time

import pytest

from app.services.metrics_service import get_metrics_service
from tests.conftest import make_client

ITERATIONS = 20


def _fid(name: str) -> str:
    return base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")


def _p95(samples: list[float]) -> float:
    ordered = sorted(samples)
    idx = max(0, int(len(ordered) * 0.95) - 1)
    return ordered[idx]


def _report(label: str, samples: list[float]) -> str:
    return (
        f"{label}: min={min(samples):.3f}s median={statistics.median(samples):.3f}s "
        f"p95={_p95(samples):.3f}s max={max(samples):.3f}s (n={len(samples)})"
    )


@pytest.mark.slow
def test_一覧の応答時間が400件規模でP95未満1秒(copied_log_dir, monkeypatch):
    """REQ-N-003. 実データを 400 件規模に増量して測定する (tmp 上で行う)。"""
    src = copied_log_dir / "sar23"
    made = 0
    for day in range(1, 32):
        for prefix in ("sar", "sa"):
            dest = copied_log_dir / f"{prefix}{day:02d}"
            if not dest.exists():
                shutil.copy2(src, dest)
                made += 1
    client = make_client(copied_log_dir, monkeypatch)
    params = {"from": "1970-01-01", "to": "2999-12-31", "perPage": 10}

    client.get("/api/log-files", params=params)  # ウォームアップ
    samples = []
    for _ in range(ITERATIONS):
        started = time.perf_counter()
        r = client.get("/api/log-files", params=params)
        samples.append(time.perf_counter() - started)
        assert r.status_code == 200

    print("\n" + _report("GET /api/log-files", samples))
    assert _p95(samples) < 1.0, _report("GET /api/log-files", samples)


@pytest.mark.slow
def test_メトリクス初回の応答時間がP95未満5秒(client):
    """REQ-N-004. 毎回キャッシュを空にして初回の所要時間を測る。"""
    service = get_metrics_service()
    samples = []
    for _ in range(ITERATIONS):
        service.clear()
        started = time.perf_counter()
        r = client.get(f"/api/log-files/{_fid('sar23')}/metrics")
        samples.append(time.perf_counter() - started)
        assert r.status_code == 200

    print("\n" + _report("GET .../metrics (初回)", samples))
    assert _p95(samples) < 5.0, _report("GET .../metrics (初回)", samples)


@pytest.mark.slow
def test_メトリクスキャッシュ命中の応答時間がP95未満1秒(client):
    """REQ-N-004."""
    client.get(f"/api/log-files/{_fid('sar23')}/metrics")  # ウォームアップ
    samples = []
    for _ in range(ITERATIONS):
        started = time.perf_counter()
        r = client.get(f"/api/log-files/{_fid('sar23')}/metrics")
        samples.append(time.perf_counter() - started)
        assert r.status_code == 200

    print("\n" + _report("GET .../metrics (キャッシュ)", samples))
    assert _p95(samples) < 1.0, _report("GET .../metrics (キャッシュ)", samples)


@pytest.mark.skip(
    reason="NOT RUN: SC-02 の初回グラフ描画時間 (REQ-N-005) は、"
    "この環境にブラウザ計測手段が無いため測定できない。合格として扱わないこと。"
)
def test_SC02の最初のグラフが3秒以内に描画される():
    raise AssertionError("未実装 (計測手段なし)")
