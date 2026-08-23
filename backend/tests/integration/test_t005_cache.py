"""T005 — キャッシュ効果 (docs/P008-test-direction/T005-cache-effect.md).

呼び出し回数の検証を所要時間の測定より優先する (時間はマシン負荷に左右されるため)。
"""

import base64
import os
import time

from app.readers import sar_text
from tests.conftest import make_client


def _fid(name: str) -> str:
    return base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")


def _spy(monkeypatch, attr: str) -> list:
    calls: list = []
    real = getattr(sar_text, attr)

    def wrapper(path):
        calls.append(path)
        return real(path)

    monkeypatch.setattr(sar_text, attr, wrapper)
    return calls


def test_一覧2回目で採取日の再読み取りが発生しない(client, monkeypatch):
    params = {"from": "2026-08-01", "to": "2026-08-31", "perPage": 100}
    client.get("/api/log-files", params=params)
    calls = _spy(monkeypatch, "read_header")
    client.get("/api/log-files", params=params)
    assert calls == [], f"{len(calls)} 回の再読み取りが発生した"


def test_メトリクス2回目でリーダが呼ばれない(client, monkeypatch):
    client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    calls = _spy(monkeypatch, "read_sar_text")
    client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    assert calls == []


def test_mtime変更で再読み取りが発生する(copied_log_dir, monkeypatch):
    c = make_client(copied_log_dir, monkeypatch)
    c.get(f"/api/log-files/{_fid('sar23')}/metrics")
    target = copied_log_dir / "sar23"
    future = time.time() + 100
    os.utime(target, (future, future))
    calls = _spy(monkeypatch, "read_sar_text")
    c.get(f"/api/log-files/{_fid('sar23')}/metrics")
    assert len(calls) == 1


def test_size変更で再読み取りが発生する(copied_log_dir, monkeypatch):
    c = make_client(copied_log_dir, monkeypatch)
    c.get(f"/api/log-files/{_fid('sar23')}/metrics")
    with (copied_log_dir / "sar23").open("a", encoding="utf-8") as fh:
        fh.write("\n")
    calls = _spy(monkeypatch, "read_sar_text")
    c.get(f"/api/log-files/{_fid('sar23')}/metrics")
    assert len(calls) == 1


def test_キャッシュ命中時の応答が1秒未満(client):
    client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    started = time.perf_counter()
    client.get(f"/api/log-files/{_fid('sar23')}/metrics")
    elapsed = time.perf_counter() - started
    assert elapsed < 1.0, f"キャッシュ命中で {elapsed:.3f}s かかった"
