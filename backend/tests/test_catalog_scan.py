"""U004-T1 / U004-T2 — 走査と採取日の解決."""
import pytest

from app.services.catalog_service import CatalogService, kind_of


def test_kind判定でsar23をsaと誤判定しない():
    assert kind_of("sar23") == "sar"
    assert kind_of("sa23") == "sa"


def test_実データで18件が列挙される(real_log_dir):
    entries = CatalogService().scan(real_log_dir)
    assert len(entries) == 18
    assert sum(1 for e in entries if e.kind == "sar") == 9
    assert sum(1 for e in entries if e.kind == "sa") == 9


def test_命名規則外は列挙されない(copied_log_dir):
    for name in ("sa1", "sa123", "saXX", "foo", "README.md"):
        (copied_log_dir / name).write_text("x", encoding="utf-8")
    names = {e.file_name for e in CatalogService().scan(copied_log_dir)}
    assert not ({"sa1", "sa123", "saXX", "foo", "README.md"} & names)


def test_サブディレクトリは走査しない(copied_log_dir):
    sub = copied_log_dir / "sub"
    sub.mkdir()
    (sub / "sar01").write_text("Linux 6.8 (h) \t2026-08-01 \t_x86_64_\t(1 CPU)\n", encoding="utf-8")
    names = {e.file_name for e in CatalogService().scan(copied_log_dir)}
    assert "sar01" not in names


def test_存在しないディレクトリで空リスト(tmp_path):
    assert CatalogService().scan(tmp_path / "nope") == []


def test_sarの採取日が1行目から取得される(real_log_dir):
    entries = {e.file_name: e for e in CatalogService().scan(real_log_dir)}
    assert entries["sar23"].date.isoformat() == "2026-08-23"
    assert entries["sar23"].hostname == "www4250uj"


def test_sadf不在ならsaはunreadableになるが例外にならない(real_log_dir):
    from app.readers.sa_binary import sadf_available

    svc = CatalogService()
    readable, unreadable = svc.counts(real_log_dir)
    assert readable + unreadable == 18
    if not sadf_available():
        assert readable == 9 and unreadable == 9


def test_採取日を取得できないファイルは一覧から除外される(copied_log_dir):
    (copied_log_dir / "sar01").write_text("壊れた行\n", encoding="utf-8")
    svc = CatalogService()
    names = {e.file_name for e in svc.readable(copied_log_dir)}
    assert "sar01" not in names


def test_キャッシュ命中時はファイルを再読み込みしない(real_log_dir, monkeypatch):
    from app.readers import sar_text

    svc = CatalogService()
    svc.scan(real_log_dir)
    calls = []
    real = sar_text.read_header
    monkeypatch.setattr(
        sar_text, "read_header", lambda p: (calls.append(p), real(p))[1]
    )
    svc.scan(real_log_dir)
    assert calls == []


def test_mtimeが変わるとキャッシュが失効する(copied_log_dir):
    import os
    import time

    svc = CatalogService()
    svc.scan(copied_log_dir)
    target = copied_log_dir / "sar23"
    future = time.time() + 100
    os.utime(target, (future, future))
    entries = {e.file_name: e for e in svc.scan(copied_log_dir)}
    assert entries["sar23"].mtime_ns == target.stat().st_mtime_ns


def test_sizeが変わるとキャッシュが失効する(copied_log_dir):
    svc = CatalogService()
    before = {e.file_name: e for e in svc.scan(copied_log_dir)}["sar23"]
    target = copied_log_dir / "sar23"
    with target.open("a", encoding="utf-8") as fh:
        fh.write("\n")
    after = {e.file_name: e for e in svc.scan(copied_log_dir)}["sar23"]
    assert after.size_bytes != before.size_bytes
