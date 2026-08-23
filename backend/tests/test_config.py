"""U001-T1"""
from app.config import DEFAULT_LOG_DIR, get_settings


def test_既定のログディレクトリが返る(monkeypatch):
    monkeypatch.delenv("SYSSTAT_LOG_DIR", raising=False)
    # Windows では str(Path("/var/log/sysstat")) が "\var\log\sysstat" になるため
    # 区切り文字を正規化して比較する。
    assert str(get_settings().log_dir).replace("\\", "/") == DEFAULT_LOG_DIR


def test_環境変数の値が反映される(monkeypatch):
    monkeypatch.setenv("SYSSTAT_LOG_DIR", "/tmp/xyz")
    assert str(get_settings().log_dir).replace("\\", "/") == "/tmp/xyz"


def test_create_appがFastAPIを返す():
    from fastapi import FastAPI
    from app.main import create_app

    assert isinstance(create_app(), FastAPI)
