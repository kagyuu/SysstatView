"""U002-T5 — 実データによる検証。

合成データではなく sysstat-log/var/log/sysstat/sar15..sar23 を通す。
この開発環境で完全に検証できる唯一の経路であり、ここは妥協しない。
"""

from pathlib import Path

import pytest

from app.readers.normalize import normalize
from app.readers.sar_text import read_sar_text

SAR_FILES = [f"sar{d}" for d in range(15, 24)]

# docs/P001-requirement.md §7 (18) + P102 で実データから発見した PSI 3 グループ。
EXPECTED_GROUP_IDS = {
    "MG-CPU", "MG-PROC", "MG-SWPIO", "MG-PAGE", "MG-IO", "MG-MEM", "MG-SWAP",
    "MG-HUGE", "MG-KTBL", "MG-LOAD", "MG-TTY", "MG-DISK", "MG-NET", "MG-NETERR",
    "MG-NFSC", "MG-NFSD", "MG-SOCK", "MG-SOFTNET",
    "MG-PSI-CPU", "MG-PSI-IO", "MG-PSI-MEM",
}


@pytest.mark.parametrize("name", SAR_FILES)
def test_全ての実データが例外なく解析できる(real_log_dir: Path, name: str):
    header, tables = read_sar_text(real_log_dir / name)
    groups = normalize(tables, file_name=name)
    assert groups, f"{name}: グループが 1 件も取れていない"


def test_sar23のヘッダ情報(real_log_dir: Path):
    header, _ = read_sar_text(real_log_dir / "sar23")
    assert header.date.isoformat() == "2026-08-23"
    assert header.hostname == "www4250uj"
    assert header.cpu_count == 3
    assert header.arch == "x86_64"


def test_sar23のグループ集合が期待どおり(real_log_dir: Path):
    _, tables = read_sar_text(real_log_dir / "sar23")
    groups = normalize(tables, file_name="sar23")
    assert {g.groupId for g in groups} == EXPECTED_GROUP_IDS


def test_MG_CPUのキーがallと各CPU番号(real_log_dir: Path):
    _, tables = read_sar_text(real_log_dir / "sar23")
    cpu = next(g for g in normalize(tables) if g.groupId == "MG-CPU")
    assert {s.key for s in cpu.series} == {"all", "0", "1", "2"}


def test_MG_CPUのサンプル数が1日分ある(real_log_dir: Path):
    """繰り返しヘッダでブロックが切れていないことの検算。

    テストデータは約 10 分間隔で 1 日分あるため 140 件以上になる。
    11 件や 13 件しか無い場合はブロックが連結できていない。
    """
    _, tables = read_sar_text(real_log_dir / "sar23")
    cpu = next(g for g in normalize(tables) if g.groupId == "MG-CPU")
    assert len(cpu.timestamps) >= 140, (
        f"timestamps が {len(cpu.timestamps)} 件しかない。"
        "繰り返しヘッダでブロックが切れている可能性がある。"
    )


def test_全グループでvaluesの長さがtimestampsと一致する(real_log_dir: Path):
    for name in SAR_FILES:
        _, tables = read_sar_text(real_log_dir / name)
        for group in normalize(tables, file_name=name):
            expected = len(group.timestamps)
            for series in group.series:
                assert len(series.values) == expected, (
                    f"{name}/{group.groupId}/{series.key}/{series.metric}: "
                    f"{len(series.values)} != {expected}"
                )


def test_Average由来の値が混入していない(real_log_dir: Path):
    _, tables = read_sar_text(real_log_dir / "sar23")
    for group in normalize(tables):
        assert not any("Average" in ts for ts in group.timestamps)


def test_MG_NETのキー数が20以上ある(real_log_dir: Path):
    """Docker 由来のインタフェースを取りこぼしていないこと。"""
    _, tables = read_sar_text(real_log_dir / "sar23")
    net = next(g for g in normalize(tables) if g.groupId == "MG-NET")
    assert len({s.key for s in net.series}) >= 20


def test_先頭サンプルの値が実ファイルの記載と一致する(real_log_dir: Path):
    """sar23 の 00:10:09 の all の %usr は 2.07 (実ファイルを直接確認した値)。"""
    _, tables = read_sar_text(real_log_dir / "sar23")
    cpu = next(g for g in normalize(tables) if g.groupId == "MG-CPU")
    series = next(s for s in cpu.series if s.key == "all" and s.metric == "%usr")
    assert cpu.timestamps[0] == "2026-08-23T00:10:09"
    assert series.values[0] == pytest.approx(2.07)


def test_timestampsが昇順で重複しない(real_log_dir: Path):
    _, tables = read_sar_text(real_log_dir / "sar23")
    for group in normalize(tables):
        assert group.timestamps == sorted(group.timestamps)
        assert len(set(group.timestamps)) == len(group.timestamps)
