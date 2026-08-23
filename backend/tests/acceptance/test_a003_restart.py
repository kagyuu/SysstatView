"""A003 — 再起動耐性 (docs/P009-acceptance-direction/A003-restart-resilience.md).

Docker が無い環境のため、ローカルプロセスとして起動・停止・再起動する形で確認する。
アプリインスタンスを作り直すことを「再起動」とみなす。
(コンテナ再起動での確認は A005 の対象であり、この環境では NOT RUN。)
"""

import base64
import json
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent
LOG_DIR = REPO_ROOT / "sysstat-log" / "var" / "log" / "sysstat"

# 別プロセスで起動 -> リクエスト -> 終了 を 1 回分行うスクリプト。
# 「2 回目の起動」という条件は、同一プロセス内では再現できない。
_PROBE = r"""
import base64, json, os, sys
sys.path.insert(0, sys.argv[1])
os.environ["SYSSTAT_LOG_DIR"] = sys.argv[2]
from fastapi.testclient import TestClient
from app.main import create_app
c = TestClient(create_app())
fid = base64.urlsafe_b64encode(b"sar23").decode().rstrip("=")
health = c.get("/api/health").json()
listing = c.get("/api/log-files", params={"from": "2026-08-01", "to": "2026-08-31", "perPage": 100}).json()
metrics = c.get(f"/api/log-files/{fid}/metrics").json()
summary = {
    "sadfAvailable": health["sadfAvailable"],
    "readableFileCount": health["readableFileCount"],
    "totalItems": listing["totalItems"],
    "groupCount": len(metrics["groups"]),
    "groupIds": sorted(g["groupId"] for g in metrics["groups"]),
    "cpuFirstValue": next(
        s["values"][0] for g in metrics["groups"] if g["groupId"] == "MG-CPU"
        for s in g["series"] if s["key"] == "all" and s["metric"] == "%usr"
    ),
    "timestampCount": next(
        len(g["timestamps"]) for g in metrics["groups"] if g["groupId"] == "MG-CPU"
    ),
}
print("RESULT:" + json.dumps(summary))
"""


def _boot_once() -> dict:
    proc = subprocess.run(
        [sys.executable, "-c", _PROBE, str(BACKEND_DIR), str(LOG_DIR)],
        capture_output=True,
        text=True,
        timeout=180,
        cwd=str(BACKEND_DIR),
    )
    assert proc.returncode == 0, (
        f"起動に失敗した (exit={proc.returncode})\nSTDERR:\n{proc.stderr[-3000:]}"
    )
    line = next(
        (l for l in proc.stdout.splitlines() if l.startswith("RESULT:")), None
    )
    assert line, f"結果を取得できなかった\nSTDOUT:\n{proc.stdout[-2000:]}"
    return json.loads(line[len("RESULT:") :])


@pytest.mark.slow
def test_3回連続で起動でき結果が毎回同一である():
    """1 回目・2 回目・3 回目の起動がいずれも成功し、応答が一致すること。

    本システムは永続データストアを持たないためマイグレーション由来の起動失敗は
    構造上生じないが、「生じないはずだ」で済ませず実際に複数回起動して確認する
    (docs/P006-test-plan.md §4.1)。
    """
    first = _boot_once()
    second = _boot_once()
    third = _boot_once()

    assert first == second, f"1 回目と 2 回目で応答が異なる\n{first}\n{second}"
    assert second == third, f"2 回目と 3 回目で応答が異なる"
    # キャッシュを失った状態から再構築できていること
    assert first["groupCount"] > 0
    assert first["timestampCount"] >= 140
    assert first["totalItems"] > 0
