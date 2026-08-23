"""テスト共通の fixture (docs/P006-test-plan.md §5).

実データ sysstat-log/var/log/sysstat/ は読み取り専用で扱い、書き換えない。
書き込みを伴うケースは tmp_path にコピーして行う。
"""

import shutil
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_DIR.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


@pytest.fixture
def real_log_dir() -> Path:
    """リポジトリに置かれた実データ。ベースラインそのもの。"""
    path = REPO_ROOT / "sysstat-log" / "var" / "log" / "sysstat"
    assert path.is_dir(), f"実データが見つかりません: {path}"
    return path


@pytest.fixture
def copied_log_dir(real_log_dir: Path, tmp_path: Path) -> Path:
    """実データのコピー。書き込み・改変を伴うテストはこちらを使う。"""
    dest = tmp_path / "sysstat"
    shutil.copytree(real_log_dir, dest)
    return dest


@pytest.fixture(autouse=True)
def _reset_service_caches():
    """テスト間でプロセス内キャッシュを持ち越さない。

    キャッシュはモジュールレベルのシングルトンであるため、明示的に初期化しないと
    「1 回目は通るが 2 回目が落ちる」種類の失敗を生む (docs/P006-test-plan.md §5.5)。
    """
    from app.services.catalog_service import get_catalog_service
    from app.services.metrics_service import get_metrics_service

    get_catalog_service().clear()
    get_metrics_service().clear()
    yield
    get_catalog_service().clear()
    get_metrics_service().clear()


@pytest.fixture
def client(monkeypatch, real_log_dir: Path):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setenv("SYSSTAT_LOG_DIR", str(real_log_dir))
    return TestClient(create_app())


def make_client(log_dir: Path, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    monkeypatch.setenv("SYSSTAT_LOG_DIR", str(log_dir))
    return TestClient(create_app())
