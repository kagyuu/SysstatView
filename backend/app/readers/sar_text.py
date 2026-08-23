"""sar テキストの解析 (docs/P003-backend-spec.md §8).

実データ (sysstat-log/var/log/sysstat/sar15..sar23) を実測して確認した書式にもとづく。

最重要の注意点:
  繰り返されるヘッダ行の直前には必ず空行が入る。つまりファイルは
  「空行で区切られたブロック」の連なりであり、各ブロックは列名ヘッダ行で始まる。
  同一の列構成を持つブロックが複数あり、それらで 1 つのメトリクスグループを成す。
  したがって「空行 = セクションの終わり」と解釈してはならない。
  (連結は normalize.py が行う。ここでは列構成ごとに RawTable を返す。)
"""

import logging
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from app.errors import ParseFailedError
from app.logging_setup import log_event
from app.metrics.catalog import KEY_LABELS
from app.readers.raw import RawRow, RawTable, SarHeader

# 1 行目の例:
#   Linux 6.8.0-106-generic (www4250uj) \t2026-08-23 \t_x86_64_\t(3 CPU)
_RE_ISO_DATE = re.compile(r"(\d{4})-(\d{2})-(\d{2})")
_RE_US_DATE = re.compile(r"(\d{2})/(\d{2})/(\d{2,4})")
_RE_PAREN = re.compile(r"\(([^)]*)\)")
_RE_KERNEL = re.compile(r"^Linux\s+(\S+)")
# arch は "_x86_64_" のようにトークン内部にもアンダースコアを含む。
# [^_\s]+ とすると内部の "_" で切れて "x86" になってしまうため、空白以外を貪欲に取る。
_RE_ARCH = re.compile(r"_([^\s]+)_")
_RE_CPU_COUNT = re.compile(r"\((\d+)\s+CPU\)")

# 時刻列: "00:10:09" または "01:50:00 PM"
_RE_TIME = re.compile(r"^(\d{1,2}):(\d{2}):(\d{2})$")

AVERAGE_TOKEN = "Average:"


def parse_header_line(line: str) -> SarHeader:
    """sar ファイルの 1 行目を解析する。

    採取日が明示されているのはこの行だけであり、データ行は時刻しか持たない。
    """
    parsed_date: date | None = None
    m = _RE_ISO_DATE.search(line)
    if m:
        parsed_date = date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    else:
        # ★FIXME★ ISO 以外の実データを入手できていないため、以下は想定にもとづく。
        m = _RE_US_DATE.search(line)
        if m:
            mm, dd, yy = int(m.group(1)), int(m.group(2)), int(m.group(3))
            if yy < 100:
                yy += 2000
            parsed_date = date(yy, mm, dd)
    if parsed_date is None:
        raise ParseFailedError(
            "sar ファイルの 1 行目から採取日を取得できませんでした。",
            detail=line.strip()[:200],
        )

    # ホスト名は最初の括弧。"(3 CPU)" を誤って拾わないよう最初の一致のみを採る。
    hostname: str | None = None
    paren = _RE_PAREN.search(line)
    if paren:
        candidate = paren.group(1).strip()
        if not _RE_CPU_COUNT.match(f"({candidate})"):
            hostname = candidate or None

    kernel_m = _RE_KERNEL.search(line)
    arch_m = _RE_ARCH.search(line)
    cpu_m = _RE_CPU_COUNT.search(line)
    return SarHeader(
        date=parsed_date,
        hostname=hostname,
        kernel=kernel_m.group(1) if kernel_m else None,
        arch=arch_m.group(1) if arch_m else None,
        cpu_count=int(cpu_m.group(1)) if cpu_m else None,
    )


def read_header(path: Path) -> SarHeader:
    """1 行目のみを読んで採取日等を返す。

    一覧表示のたびにファイル全体を読まないための入口 (REQ-N-016)。
    """
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        first_line = fh.readline()
    if not first_line:
        raise ParseFailedError("sar ファイルが空です。", detail=str(path.name))
    return parse_header_line(first_line)


def _parse_time(token: str, ampm: str | None) -> tuple[int, int, int] | None:
    m = _RE_TIME.match(token)
    if not m:
        return None
    hh, mm, ss = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if ampm:
        upper = ampm.upper()
        if upper == "PM" and hh != 12:
            hh += 12
        elif upper == "AM" and hh == 12:
            hh = 0
    if not (0 <= hh <= 23 and 0 <= mm <= 59 and 0 <= ss <= 59):
        return None
    return hh, mm, ss


def _to_float(token: str) -> float | None:
    """数値化できない値は None にする。行ごと捨てない。"""
    try:
        return float(token)
    except ValueError:
        return None


class _Block:
    """空行で区切られた 1 ブロック。列名ヘッダ行 + データ行。"""

    def __init__(self, header_tokens: list[str]) -> None:
        # header_tokens[0] は時刻または "Average:"。
        rest = header_tokens[1:]
        # AM/PM ロケールではヘッダ行の時刻にも "AM"/"PM" が独立トークンで続く
        # (例: "12:00:00 AM   CPU   %usr")。データ行と同様に読み飛ばす。
        if rest and rest[0].upper() in ("AM", "PM"):
            rest = rest[1:]
        if rest and rest[0] in KEY_LABELS:
            self.key_label: str | None = rest[0]
            self.columns: list[str] = rest[1:]
        else:
            self.key_label = None
            self.columns = rest


def read_sar_text(path: Path) -> tuple[SarHeader, list[RawTable]]:
    """sar テキストを解析して中間表現に変換する。"""
    with path.open("r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    if not lines:
        raise ParseFailedError("sar ファイルが空です。", detail=str(path.name))

    header = parse_header_line(lines[0])
    return header, _parse_body(lines[1:], header, path.name)


def _parse_body(
    lines: list[str], header: SarHeader, file_name: str
) -> list[RawTable]:
    tables: list[RawTable] = []
    # 同一の (key_label, columns) を持つブロックは 1 つの RawTable にまとめる。
    # 繰り返しヘッダによるブロック分割をここで吸収する。
    by_signature: dict[tuple[str | None, tuple[str, ...]], RawTable] = {}

    current: _Block | None = None
    expect_header = True  # 空行の直後は必ず列名ヘッダ行
    broken_rows = 0
    # 日跨ぎ判定はメトリクスグループ (列構成) ごとに行う。
    # ファイル内では CPU セクションが 23:50 まで並んだ後、次のセクションが再び 00:00 から
    # 始まる。時刻の巻き戻りを全体で共有して見ると、セクションが変わるたびに
    # 「日をまたいだ」と誤判定してしまう。
    Signature = tuple[str | None, tuple[str, ...]]
    date_state: dict[Signature, tuple[date, int]] = {}

    for raw_line in lines:
        if not raw_line.strip():
            # ブロックの区切り。次の非空行は必ず列名ヘッダ行である。
            current = None
            expect_header = True
            continue

        tokens = raw_line.split()
        if not tokens:
            continue

        if expect_header:
            current = _Block(tokens)
            expect_header = False
            # Average: ブロックのヘッダも同じ形で現れる。データ行側で弾く。
            continue

        if current is None:
            continue

        # Average: 行は期間平均であり時系列サンプルではない (REQ-F-028)。
        if tokens[0] == AVERAGE_TOKEN:
            continue

        # 時刻の解析。AM/PM が独立トークンで続く場合がある。
        ampm: str | None = None
        idx = 1
        if len(tokens) > 1 and tokens[1].upper() in ("AM", "PM"):
            ampm = tokens[1]
            idx = 2
        parsed = _parse_time(tokens[0], ampm)
        if parsed is None:
            continue
        hh, mm, ss = parsed

        signature: Signature = (current.key_label, tuple(current.columns))
        seconds = hh * 3600 + mm * 60 + ss
        prev = date_state.get(signature)
        if prev is None:
            current_date = header.date
        else:
            current_date, last_seconds = prev
            if seconds < last_seconds:
                # 同一セクション内で時刻が巻き戻ったら日をまたいだとみなす。
                # ★FIXME★ テストデータは日をまたがないため実データで未検証。
                current_date = current_date + timedelta(days=1)
        date_state[signature] = (current_date, seconds)

        timestamp = datetime(
            current_date.year, current_date.month, current_date.day, hh, mm, ss
        ).strftime("%Y-%m-%dT%H:%M:%S")

        rest = tokens[idx:]
        key: str | None = None
        if current.key_label is not None:
            if not rest:
                broken_rows += 1
                continue
            key = rest[0]
            rest = rest[1:]

        if len(rest) != len(current.columns):
            # 列数が合わない行は破損行として読み飛ばす。
            broken_rows += 1
            continue

        table = by_signature.get(signature)
        if table is None:
            table = RawTable(
                columns=list(current.columns), key_label=current.key_label
            )
            by_signature[signature] = table
            tables.append(table)
        table.rows.append(
            RawRow(
                timestamp=timestamp,
                key=key,
                values={
                    col: _to_float(tok) for col, tok in zip(current.columns, rest)
                },
            )
        )

    if broken_rows:
        log_event(
            logging.WARNING,
            "reader.broken_rows",
            "列数が一致しない行を読み飛ばしました。",
            fileName=file_name,
            brokenRows=broken_rows,
        )
    return tables
