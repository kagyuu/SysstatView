"""U002-T4 — 正規化と不変条件 (INV-1〜INV-5)."""

import pytest

from app.errors import InternalError
from app.models import MetricGroup, Series
from app.readers.normalize import _verify_invariants, normalize
from app.readers.raw import RawRow, RawTable


def _cpu_table(rows):
    return RawTable(columns=["%usr", "%sys"], key_label="CPU", rows=rows)


def test_同一グループの複数RawTableが連結される():
    t1 = _cpu_table(
        [RawRow("2026-08-23T00:10:00", "all", {"%usr": 1.0, "%sys": 0.5})]
    )
    t2 = _cpu_table(
        [RawRow("2026-08-23T00:20:00", "all", {"%usr": 2.0, "%sys": 0.6})]
    )
    groups = normalize([t1, t2])
    assert len(groups) == 1
    assert groups[0].timestamps == ["2026-08-23T00:10:00", "2026-08-23T00:20:00"]
    usr = next(s for s in groups[0].series if s.metric == "%usr")
    assert usr.values == [1.0, 2.0]


def test_timestampsが昇順で重複排除される():
    rows = [
        RawRow("2026-08-23T00:20:00", "all", {"%usr": 2.0, "%sys": 0.0}),
        RawRow("2026-08-23T00:10:00", "all", {"%usr": 1.0, "%sys": 0.0}),
        RawRow("2026-08-23T00:20:00", "0", {"%usr": 9.0, "%sys": 0.0}),
    ]
    g = normalize([_cpu_table(rows)])[0]
    assert g.timestamps == ["2026-08-23T00:10:00", "2026-08-23T00:20:00"]


def test_一部のキーにだけあるサンプルはNoneで埋まる():
    rows = [
        RawRow("2026-08-23T00:10:00", "all", {"%usr": 1.0, "%sys": 0.0}),
        RawRow("2026-08-23T00:20:00", "all", {"%usr": 2.0, "%sys": 0.0}),
        RawRow("2026-08-23T00:20:00", "0", {"%usr": 9.0, "%sys": 0.0}),
    ]
    g = normalize([_cpu_table(rows)])[0]
    cpu0 = next(s for s in g.series if s.key == "0" and s.metric == "%usr")
    assert cpu0.values == [None, 9.0]
    assert len(cpu0.values) == len(g.timestamps)


def test_キーなしグループのkeyはすべてNone():
    t = RawTable(
        columns=["proc/s", "cswch/s"],
        key_label=None,
        rows=[RawRow("2026-08-23T00:10:00", None, {"proc/s": 1.0, "cswch/s": 2.0})],
    )
    g = normalize([t])[0]
    assert g.keyLabel is None
    assert all(s.key is None for s in g.series)


def test_未知の列構成は無視され他のグループは返る():
    unknown = RawTable(
        columns=["zzz-unknown"],
        key_label=None,
        rows=[RawRow("2026-08-23T00:10:00", None, {"zzz-unknown": 1.0})],
    )
    known = RawTable(
        columns=["proc/s", "cswch/s"],
        key_label=None,
        rows=[RawRow("2026-08-23T00:10:00", None, {"proc/s": 1.0, "cswch/s": 2.0})],
    )
    groups = normalize([unknown, known])
    assert [g.groupId for g in groups] == ["MG-PROC"]


def test_行が空のグループは結果に含まれない():
    assert normalize([_cpu_table([])]) == []


def test_出力順がdisplayOrderに従う():
    mem = RawTable(
        columns=["kbmemfree"],
        key_label=None,
        rows=[RawRow("2026-08-23T00:10:00", None, {"kbmemfree": 1.0})],
    )
    cpu = _cpu_table([RawRow("2026-08-23T00:10:00", "all", {"%usr": 1.0, "%sys": 0.0})])
    # 入力順を逆にしても出力は displayOrder 順 (MG-CPU=1, MG-MEM=6)
    groups = normalize([mem, cpu])
    assert [g.groupId for g in groups] == ["MG-CPU", "MG-MEM"]


def test_単位が付与される():
    g = normalize([_cpu_table([RawRow("2026-08-23T00:10:00", "all", {"%usr": 1.0, "%sys": 0.0})])])[0]
    assert next(s for s in g.series if s.metric == "%usr").unit == "%"


# --- INV 違反の検出 ---


def test_INV1_valuesの長さ不一致を検出する():
    g = MetricGroup(
        groupId="MG-CPU",
        keyLabel="CPU",
        timestamps=["2026-08-23T00:10:00", "2026-08-23T00:20:00"],
        series=[Series(key="all", metric="%usr", unit="%", values=[1.0])],
    )
    with pytest.raises(InternalError):
        _verify_invariants([g])


def test_INV2_timestampsが昇順でないことを検出する():
    g = MetricGroup(
        groupId="MG-CPU",
        keyLabel="CPU",
        timestamps=["2026-08-23T00:20:00", "2026-08-23T00:10:00"],
        series=[Series(key="all", metric="%usr", unit="%", values=[1.0, 2.0])],
    )
    with pytest.raises(InternalError):
        _verify_invariants([g])


def test_INV3_キーなしグループにkeyがあることを検出する():
    g = MetricGroup(
        groupId="MG-PROC",
        keyLabel=None,
        timestamps=["2026-08-23T00:10:00"],
        series=[Series(key="all", metric="proc/s", unit="/s", values=[1.0])],
    )
    with pytest.raises(InternalError):
        _verify_invariants([g])


def test_INV4_未定義のgroupIdを検出する():
    g = MetricGroup(
        groupId="MG-NOT-EXIST",
        keyLabel=None,
        timestamps=["2026-08-23T00:10:00"],
        series=[Series(key=None, metric="x", unit=None, values=[1.0])],
    )
    with pytest.raises(InternalError):
        _verify_invariants([g])


def test_INV5_seriesが空のグループを検出する():
    g = MetricGroup(
        groupId="MG-PROC", keyLabel=None, timestamps=["2026-08-23T00:10:00"], series=[]
    )
    with pytest.raises(InternalError):
        _verify_invariants([g])
