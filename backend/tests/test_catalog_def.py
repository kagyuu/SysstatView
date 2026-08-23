"""U001-T4 — メトリクス定義と対応表."""
import pytest

from app.metrics.catalog import (
    GROUP_BY_ID,
    GROUP_DEFS,
    SADF_FIELD_TO_METRIC,
    SADF_KEY_TO_GROUP,
    identify_group_from_sar,
    unit_for,
)


def test_グループが定義されdisplayOrderが重複しない():
    assert len(GROUP_DEFS) == 21
    orders = [g.displayOrder for g in GROUP_DEFS]
    assert len(set(orders)) == len(orders)
    assert len(set(g.groupId for g in GROUP_DEFS)) == len(GROUP_DEFS)


@pytest.mark.parametrize(
    "name,expected",
    [
        ("%usr", "%"), ("%vmeff", "%"), ("kbmemfree", "KB"), ("kbhugfree", "KB"),
        ("rxkB/s", "KB/s"), ("wkB/s", "KB/s"), ("proc/s", "/s"), ("await", "ms"),
        ("ldavg-1", None), ("totsck", None), ("%scpu-10", "%"),
    ],
)
def test_単位の割り当て規則(name, expected):
    assert unit_for(name) == expected


def test_MG_NETとMG_NETERRを識別列で区別する():
    net = identify_group_from_sar(["rxpck/s", "txpck/s", "rxkB/s"], "IFACE")
    err = identify_group_from_sar(["rxerr/s", "txerr/s", "coll/s"], "IFACE")
    assert net == "MG-NET"
    assert err == "MG-NETERR"


def test_MG_IOとMG_DISKをキー列で区別する():
    assert identify_group_from_sar(["tps", "bread/s", "bwrtn/s"], None) == "MG-IO"
    assert identify_group_from_sar(["tps", "%util", "await"], "DEV") == "MG-DISK"


def test_列順を入れ替えても同じ結果になる():
    a = identify_group_from_sar(["%usr", "%sys", "%idle"], "CPU")
    b = identify_group_from_sar(["%idle", "%sys", "%usr"], "CPU")
    assert a == b == "MG-CPU"


def test_未知の列構成はNoneを返す():
    assert identify_group_from_sar(["zzz"], None) is None


def test_PSIグループが識別される():
    assert identify_group_from_sar(["%scpu-10", "%scpu"], None) == "MG-PSI-CPU"
    assert identify_group_from_sar(["%sio-10", "%fio"], None) == "MG-PSI-IO"
    assert identify_group_from_sar(["%smem-10", "%fmem"], None) == "MG-PSI-MEM"


def test_sadf対応表の値がすべて定義済みグループを指す():
    for key, group_id in SADF_KEY_TO_GROUP.items():
        assert group_id in GROUP_BY_ID, f"{key} -> {group_id} が未定義"


def test_sadfフィールド対応表に重複した指標名の衝突がない():
    # 同じ sar 指標名に複数の sadf フィールドが対応していないこと
    seen: dict[str, str] = {}
    for field, metric in SADF_FIELD_TO_METRIC.items():
        assert metric not in seen, f"{metric} が {seen.get(metric)} と {field} で重複"
        seen[metric] = field
