"""U003-T1 / U003-T2 / U003-T3 — sa 経路。

この開発環境には sadf が無いため、subprocess をモックしフィクスチャで検証する。
「実 sadf の出力で確認した」とは記録しないこと (docs/P006-test-plan.md §6.2)。
"""

import json
import subprocess
from pathlib import Path

import pytest

from app.errors import ParseFailedError, SadfFailedError, SadfUnavailableError
from app.readers import sa_binary
from app.readers.normalize import normalize

FIXTURE = Path(__file__).parent / "fixtures" / "sadf_sample.json"


class _Proc:
    def __init__(self, stdout="", stderr="", returncode=0):
        self.stdout = stdout
        self.stderr = stderr
        self.returncode = returncode


# --- U003-T1: 起動ラッパ ---


def test_argvが配列でshellを使わない(monkeypatch, tmp_path):
    captured = {}

    def fake_run(argv, **kwargs):
        captured["argv"] = argv
        captured["kwargs"] = kwargs
        return _Proc(stdout="{}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    sa_binary.run_sadf(tmp_path / "sa23", ["-j", "--", "-A"])

    assert isinstance(captured["argv"], list)
    assert captured["argv"][0] == "sadf"
    assert captured["kwargs"].get("shell") is False


def test_LC_ALLがCに設定される(monkeypatch, tmp_path):
    captured = {}

    def fake_run(argv, **kwargs):
        captured["env"] = kwargs.get("env")
        return _Proc(stdout="{}")

    monkeypatch.setattr(subprocess, "run", fake_run)
    sa_binary.run_sadf(tmp_path / "sa23")
    assert captured["env"]["LC_ALL"] == "C"


def test_コマンド不在はSadfUnavailableError(monkeypatch, tmp_path):
    def fake_run(argv, **kwargs):
        raise FileNotFoundError("sadf")

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SadfUnavailableError) as e:
        sa_binary.run_sadf(tmp_path / "sa23")
    assert e.value.http_status == 503


def test_タイムアウトはSadfFailedError(monkeypatch, tmp_path):
    def fake_run(argv, **kwargs):
        raise subprocess.TimeoutExpired(cmd="sadf", timeout=60)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SadfFailedError):
        sa_binary.run_sadf(tmp_path / "sa23")


def test_非0終了はSadfFailedErrorでstderrがdetailに載る(monkeypatch, tmp_path):
    def fake_run(argv, **kwargs):
        return _Proc(stderr="Invalid system activity file", returncode=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(SadfFailedError) as e:
        sa_binary.run_sadf(tmp_path / "sa23")
    assert "Invalid system activity file" in e.value.detail


# --- U003-T2 / T3: JSON 変換 ---


@pytest.fixture
def sadf_stdout() -> str:
    return FIXTURE.read_text(encoding="utf-8")


@pytest.fixture
def patched(monkeypatch, sadf_stdout):
    monkeypatch.setattr(
        subprocess, "run", lambda argv, **kw: _Proc(stdout=sadf_stdout)
    )


def test_ヘッダが組まれる(patched, tmp_path):
    header, _ = sa_binary.read_sa_binary(tmp_path / "sa23")
    assert header.date.isoformat() == "2026-08-23"
    assert header.hostname == "www4250uj"
    assert header.kernel == "6.8.0-106-generic"
    assert header.arch == "x86_64"
    assert header.cpu_count == 3


def test_キー付き統計にkey_labelとkeyが入る(patched, tmp_path):
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    cpu = next(t for t in tables if "%usr" in t.columns)
    assert cpu.key_label == "CPU"
    assert {r.key for r in cpu.rows} == {"all", "0", "1", "2"}


def test_キーなし統計はkey_labelがNone(patched, tmp_path):
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    mem = next(t for t in tables if "kbmemfree" in t.columns)
    assert mem.key_label is None
    assert all(r.key is None for r in mem.rows)


def test_フィールド名がsar表記に読み替えられる(patched, tmp_path):
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    cpu = next(t for t in tables if "%usr" in t.columns)
    assert "user" not in cpu.columns
    assert "%usr" in cpu.columns


def test_ネストキーnetwork_net_devが解決される(patched, tmp_path):
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    net = next(t for t in tables if "rxpck/s" in t.columns)
    assert net.key_label == "IFACE"
    assert {r.key for r in net.rows} == {"ens3", "docker0"}


def test_未知の統計種別が無視され他は失われない(patched, tmp_path):
    """フィクスチャに unknown-future-stat を仕込んである。"""
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    assert tables, "未知キーの存在で全体が失われている"
    assert any("%usr" in t.columns for t in tables)


def test_memoryのswap系がMG_SWAPに切り出される(patched, tmp_path):
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    swap = next(t for t in tables if "kbswpfree" in t.columns)
    mem = next(t for t in tables if "kbmemfree" in t.columns)
    assert "kbswpfree" not in mem.columns


def test_normalizeを通してMetricGroupが得られる(patched, tmp_path):
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    groups = normalize(tables, file_name="sa23")
    assert {g.groupId for g in groups} >= {"MG-CPU", "MG-MEM", "MG-DISK", "MG-NET"}


def test_sa経路でもINV1が成立する(patched, tmp_path):
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    for group in normalize(tables):
        for series in group.series:
            assert len(series.values) == len(group.timestamps)


def test_値がsar23の実測値と一致する(patched, tmp_path):
    """フィクスチャは sar23 の先頭サンプルに合わせてある。

    将来 sadf が使える環境で 2 経路の一致 (T002) を実行する際の基準。
    """
    _, tables = sa_binary.read_sa_binary(tmp_path / "sa23")
    cpu = next(g for g in normalize(tables) if g.groupId == "MG-CPU")
    series = next(s for s in cpu.series if s.key == "all" and s.metric == "%usr")
    assert series.values[0] == pytest.approx(2.07)
    assert cpu.timestamps[0] == "2026-08-23T00:10:09"


def test_JSONとして壊れた出力はParseFailedError(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run", lambda argv, **kw: _Proc(stdout="not json")
    )
    with pytest.raises(ParseFailedError):
        sa_binary.read_sa_binary(tmp_path / "sa23")


def test_想定した構造が無い場合はParseFailedError(monkeypatch, tmp_path):
    monkeypatch.setattr(
        subprocess, "run", lambda argv, **kw: _Proc(stdout=json.dumps({"x": 1}))
    )
    with pytest.raises(ParseFailedError):
        sa_binary.read_sa_binary(tmp_path / "sa23")
