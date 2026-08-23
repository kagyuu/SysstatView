"""中間表現 -> API 応答への正規化 (docs/P003-backend-spec.md §7.3, §4.2).

sa 経路と sar 経路の双方がこの関数を通る。ここに経路固有の処理を書かない。
不変条件 INV-1〜INV-5 は assert ではなく明示的に検証し、違反時に例外を投げる。
"""

import logging

from app.errors import InternalError
from app.logging_setup import log_event
from app.metrics.catalog import (
    GROUP_BY_ID,
    identify_group_from_sar,
    unit_for,
)
from app.models import MetricGroup, Series
from app.readers.raw import RawTable


def normalize(tables: list[RawTable], *, file_name: str = "") -> list[MetricGroup]:
    # 1. groupId を決め、2. 同一 groupId の行を連結する。
    #    (sar の繰り返しヘッダに由来するブロック分割をここで吸収する)
    rows_by_group: dict[str, list] = {}
    key_label_by_group: dict[str, str | None] = {}
    columns_by_group: dict[str, list[str]] = {}

    for table in tables:
        group_id = identify_group_from_sar(table.columns, table.key_label)
        if group_id is None:
            # 未知の列構成はファイル全体の読み取りを失敗させず、無視して記録する。
            log_event(
                logging.WARNING,
                "reader.unknown_group",
                "対応するメトリクスグループが無い表を無視しました。",
                fileName=file_name,
                keyLabel=table.key_label,
                columns=table.columns[:8],
            )
            continue
        rows_by_group.setdefault(group_id, []).extend(table.rows)
        key_label_by_group[group_id] = table.key_label
        merged = columns_by_group.setdefault(group_id, [])
        for col in table.columns:
            if col not in merged:
                merged.append(col)

    groups: list[MetricGroup] = []
    for group_id, rows in rows_by_group.items():
        if not rows:
            continue
        key_label = key_label_by_group[group_id]

        # 3. timestamps を昇順・重複排除で構築する。
        timestamps = sorted({row.timestamp for row in rows})
        index_of = {ts: i for i, ts in enumerate(timestamps)}

        # 4. (key, metric) ごとに timestamps と同じ長さの values を作る。
        #    該当サンプルが無い添字は None のまま残す。
        columns = columns_by_group[group_id]
        buckets: dict[tuple[str | None, str], list[float | None]] = {}
        seen_keys: list[str | None] = []
        for row in rows:
            if row.key not in seen_keys:
                seen_keys.append(row.key)
            idx = index_of[row.timestamp]
            for metric in columns:
                if metric not in row.values:
                    continue
                bucket = buckets.get((row.key, metric))
                if bucket is None:
                    bucket = [None] * len(timestamps)
                    buckets[(row.key, metric)] = bucket
                bucket[idx] = row.values[metric]

        series = [
            Series(
                key=key,
                metric=metric,
                unit=unit_for(metric),
                values=values,
            )
            # 出力順を安定させる: キーの出現順 -> 列の定義順
            for key in seen_keys
            for metric in columns
            if (values := buckets.get((key, metric))) is not None
        ]

        # INV-5: series が空のグループは含めない。
        if not series:
            continue

        groups.append(
            MetricGroup(
                groupId=group_id,
                keyLabel=key_label,
                timestamps=timestamps,
                series=series,
            )
        )

    _verify_invariants(groups)

    # 6. displayOrder で並べる。
    groups.sort(key=lambda g: GROUP_BY_ID[g.groupId].displayOrder)
    return groups


def _verify_invariants(groups: list[MetricGroup]) -> None:
    for group in groups:
        expected = len(group.timestamps)

        # INV-4: groupId が定義に存在する。
        if group.groupId not in GROUP_BY_ID:
            raise InternalError(
                "サーバ内部でエラーが発生しました。",
                hint=None,
            )

        # INV-2: timestamps が昇順かつ重複なし。
        for i in range(1, expected):
            if group.timestamps[i - 1] >= group.timestamps[i]:
                raise InternalError("サーバ内部でエラーが発生しました。")

        for series in group.series:
            # INV-1: values の長さが timestamps と一致する。
            if len(series.values) != expected:
                raise InternalError("サーバ内部でエラーが発生しました。")
            # INV-3: keyLabel が None のグループの key はすべて None。
            if group.keyLabel is None and series.key is not None:
                raise InternalError("サーバ内部でエラーが発生しました。")

        # INV-5: series が空のグループは含まれない。
        if not group.series:
            raise InternalError("サーバ内部でエラーが発生しました。")
