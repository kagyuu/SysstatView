"""sa バイナリの読み取り (docs/P003-backend-spec.md §9 / ADR-002).

sadf コマンドを subprocess で起動し、JSON 出力を中間表現へ変換する。
正規化は行わない。normalize() (readers/normalize.py) をそのまま使う (REQ-F-024)。

★FIXME★ この開発環境には sadf が無く (docs/ArchitectureHandbook.md §9-1)、
sadf -j の実出力による確認ができていない。フィールド名は sysstat の公開仕様に
もとづく記述である。sadf が使える環境での初回実行時に確認すること。
"""

import json
import logging
import os
import shutil
import subprocess
import time
from datetime import date, datetime
from pathlib import Path

from app.errors import ParseFailedError, SadfFailedError, SadfUnavailableError
from app.logging_setup import log_event
from app.metrics.catalog import (
    SADF_FIELD_TO_METRIC,
    SADF_KEY_FIELD,
    SADF_KEY_TO_GROUP,
    SWAP_METRICS,
    GROUP_BY_ID,
)
from app.readers.raw import RawRow, RawTable, SarHeader

SADF_TIMEOUT_SECONDS = 60  # ★FIXME★ 値は想定


def sadf_available() -> bool:
    return shutil.which("sadf") is not None


def sadf_version() -> str | None:
    if not sadf_available():
        return None
    try:
        proc = subprocess.run(
            ["sadf", "-V"],
            shell=False,
            capture_output=True,
            text=True,
            timeout=10,
            env=_sadf_env(),
        )
    except (OSError, subprocess.SubprocessError):
        return None
    output = (proc.stdout or proc.stderr or "").strip()
    return output.splitlines()[0] if output else None


def _sadf_env() -> dict[str, str]:
    # ロケールによる出力差異を排除する。
    env = dict(os.environ)
    env["LC_ALL"] = "C"
    return env


def run_sadf(path: Path, extra_args: list[str] | None = None) -> str:
    """sadf を起動して標準出力を返す。

    引数は必ず配列で渡し、シェルを介さない (REQ-N-008)。
    """
    argv = ["sadf", *(extra_args or []), str(path)]
    started = time.perf_counter()
    try:
        proc = subprocess.run(
            argv,
            shell=False,
            capture_output=True,
            text=True,
            timeout=SADF_TIMEOUT_SECONDS,
            env=_sadf_env(),
        )
    except FileNotFoundError as exc:
        raise SadfUnavailableError(
            "sa ファイルの読み取りに必要な sadf コマンドが見つかりません。",
            detail=str(exc),
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise SadfFailedError(
            "sa ファイルの読み取りがタイムアウトしました。",
            detail=f"sadf timed out after {SADF_TIMEOUT_SECONDS}s",
        ) from exc

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    log_event(
        logging.INFO,
        "sadf.exec",
        "sadf を実行しました。",
        argv=argv,
        returncode=proc.returncode,
        durationMs=duration_ms,
    )
    if proc.returncode != 0:
        raise SadfFailedError(
            "sa ファイルの読み取りに失敗しました。",
            detail=(proc.stderr or "").strip()[:500] or f"exit code {proc.returncode}",
        )
    return proc.stdout


def read_sa_date(path: Path) -> SarHeader:
    """一覧表示用に採取日だけを取得する (docs/P003-backend-spec.md §6.2).

    ★FIXME★ sadf -H の出力形式を実出力で確認できていないため、
    JSON (-j) を優先し、失敗した場合に -H のテキストから日付を拾う実装とする。
    """
    output = run_sadf(path, ["-j", "--", "-u"])
    return _header_from_json(output, path.name)


def read_sa_binary(path: Path) -> tuple[SarHeader, list[RawTable]]:
    """sa ファイル全体を読み、中間表現へ変換する。"""
    output = run_sadf(path, ["-j", "--", "-A"])
    header = _header_from_json(output, path.name)
    tables = _tables_from_json(output, path.name)
    return header, tables


def _host_node(output: str, file_name: str) -> dict:
    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        raise ParseFailedError(
            "sadf の出力を JSON として解釈できませんでした。",
            detail=f"{file_name}: {exc}",
        ) from exc
    try:
        hosts = data["sysstat"]["hosts"]
        if not hosts:
            raise KeyError("hosts is empty")
        return hosts[0]
    except (KeyError, TypeError) as exc:
        raise ParseFailedError(
            "sadf の出力に想定した構造がありません。",
            detail=f"{file_name}: {exc}",
        ) from exc


def _header_from_json(output: str, file_name: str) -> SarHeader:
    host = _host_node(output, file_name)
    raw_date = host.get("file-date")
    parsed: date | None = None
    if isinstance(raw_date, str):
        for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
            try:
                parsed = datetime.strptime(raw_date, fmt).date()
                break
            except ValueError:
                continue
    if parsed is None:
        raise ParseFailedError(
            "sadf の出力から採取日を取得できませんでした。",
            detail=f"{file_name}: file-date={raw_date!r}",
        )
    cpu_count = host.get("number-of-cpus")
    return SarHeader(
        date=parsed,
        hostname=host.get("nodename") or None,
        kernel=host.get("release") or None,
        arch=host.get("machine") or None,
        cpu_count=int(cpu_count) if isinstance(cpu_count, (int, float)) else None,
    )


def _iter_stat_entries(sample: dict):
    """1 サンプルの中の統計種別を (対応表のキー, 値) で列挙する。

    network のようにネストするキーは 'network.net-dev' の形に展開する。
    """
    for key, value in sample.items():
        if key == "timestamp":
            continue
        dotted = key
        if isinstance(value, dict) and dotted not in SADF_KEY_TO_GROUP:
            # ネストしたコンテナ (network など)
            nested_any = False
            for sub_key, sub_value in value.items():
                nested = f"{key}.{sub_key}"
                if nested in SADF_KEY_TO_GROUP:
                    nested_any = True
                    yield nested, sub_value
            if nested_any:
                continue
        yield dotted, value


def _timestamp_of(sample: dict, file_name: str) -> str | None:
    ts = sample.get("timestamp")
    if not isinstance(ts, dict):
        return None
    d, t = ts.get("date"), ts.get("time")
    if not isinstance(d, str) or not isinstance(t, str):
        return None
    return f"{d}T{t}"


def _tables_from_json(output: str, file_name: str) -> list[RawTable]:
    host = _host_node(output, file_name)
    statistics = host.get("statistics") or []

    tables: dict[str, RawTable] = {}
    unknown_keys: set[str] = set()
    unknown_fields: set[str] = set()

    def table_for(group_id: str) -> RawTable:
        table = tables.get(group_id)
        if table is None:
            table = RawTable(
                columns=[], key_label=GROUP_BY_ID[group_id].keyLabel, rows=[]
            )
            tables[group_id] = table
        return table

    def add_row(group_id: str, timestamp: str, key: str | None, values: dict) -> None:
        if not values:
            return
        table = table_for(group_id)
        for metric in values:
            if metric not in table.columns:
                table.columns.append(metric)
        table.rows.append(RawRow(timestamp=timestamp, key=key, values=values))

    for sample in statistics:
        if not isinstance(sample, dict):
            continue
        timestamp = _timestamp_of(sample, file_name)
        if timestamp is None:
            continue

        for stat_key, stat_value in _iter_stat_entries(sample):
            group_id = SADF_KEY_TO_GROUP.get(stat_key)
            if group_id is None:
                unknown_keys.add(stat_key)
                continue
            key_field = SADF_KEY_FIELD.get(stat_key)
            entries = stat_value if isinstance(stat_value, list) else [stat_value]
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                key = None
                if key_field is not None:
                    key_value = entry.get(key_field)
                    key = str(key_value) if key_value is not None else None
                main: dict[str, float | None] = {}
                swap: dict[str, float | None] = {}
                for field_name, value in entry.items():
                    if field_name == key_field:
                        continue
                    metric = SADF_FIELD_TO_METRIC.get(field_name)
                    if metric is None:
                        unknown_fields.add(f"{stat_key}.{field_name}")
                        continue
                    numeric = value if isinstance(value, (int, float)) else None
                    # MG-SWAP は sadf では memory キーの中に同居しうるため切り出す
                    # (docs/P003-backend-spec.md §15 #1)。
                    if group_id == "MG-MEM" and metric in SWAP_METRICS:
                        swap[metric] = numeric
                    else:
                        main[metric] = numeric
                add_row(group_id, timestamp, key, main)
                if swap:
                    add_row("MG-SWAP", timestamp, None, swap)

    if unknown_keys:
        log_event(
            logging.WARNING,
            "reader.unknown_group",
            "対応表に無い統計種別を無視しました。",
            fileName=file_name,
            keys=sorted(unknown_keys)[:20],
        )
    if unknown_fields:
        log_event(
            logging.WARNING,
            "reader.unknown_field",
            "対応表に無いフィールドを無視しました。",
            fileName=file_name,
            fields=sorted(unknown_fields)[:20],
        )
    return list(tables.values())
