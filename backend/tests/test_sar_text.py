"""U002-T2 / U002-T3 — sar テキスト解析。

本システムで実装が最も誤りやすい箇所を、小さな合成テキストで検証する。
実データ全体での検証は test_sar_realdata.py が行う。
"""

from pathlib import Path

import pytest

from app.errors import ParseFailedError
from app.readers.sar_text import parse_header_line, read_header, read_sar_text

HEADER = "Linux 6.8.0-106-generic (www4250uj) \t2026-08-23 \t_x86_64_\t(3 CPU)"


def _write(tmp_path: Path, body: str, name: str = "sar23") -> Path:
    path = tmp_path / name
    path.write_text(HEADER + "\n" + body, encoding="utf-8")
    return path


# --- U002-T2: ヘッダ行 ---


def test_1行目から採取日とホスト情報を取得する():
    h = parse_header_line(HEADER)
    assert h.date.isoformat() == "2026-08-23"
    assert h.hostname == "www4250uj"
    assert h.kernel == "6.8.0-106-generic"
    assert h.arch == "x86_64"  # "_x86_64_" の内部の "_" で切れないこと
    assert h.cpu_count == 3


def test_ホスト名として3CPUを誤って拾わない():
    line = "Linux 6.8.0 \t2026-08-23 \t_x86_64_\t(3 CPU)"
    assert parse_header_line(line).hostname != "3 CPU"


def test_日付が無い行はParseFailedError():
    with pytest.raises(ParseFailedError):
        parse_header_line("Linux 6.8.0 (host) _x86_64_ (3 CPU)")


def test_read_headerは1行目のみを読む(tmp_path, monkeypatch):
    path = _write(tmp_path, "\n00:00:02   CPU  %usr\n00:10:00   all  1.0\n")
    read_lines: list[int] = []
    real_open = Path.open

    def spy_open(self, *args, **kwargs):
        fh = real_open(self, *args, **kwargs)
        real_read = fh.read

        def guard(*a, **k):
            read_lines.append(1)
            return real_read(*a, **k)

        fh.read = guard
        return fh

    monkeypatch.setattr(Path, "open", spy_open)
    h = read_header(path)
    assert h.date.isoformat() == "2026-08-23"
    # readline のみを使い、read() でファイル全体を読み込んでいないこと
    assert read_lines == []


# --- U002-T3: ブロック分割とデータ行 ---


def test_繰り返しヘッダをまたいでブロックが連結される(tmp_path):
    """空行 + 同一列構成のヘッダ行が再出現しても、両ブロックの行が取れること。

    これを誤ると 1 グループ分のサンプルが最初のブロック分しか取れない。
    """
    body = (
        "\n"
        "00:00:02   CPU  %usr  %sys\n"
        "00:10:00   all   1.0   2.0\n"
        "00:20:00   all   1.1   2.1\n"
        "\n"
        "00:20:00   CPU  %usr  %sys\n"
        "00:30:00   all   1.2   2.2\n"
        "00:40:00   all   1.3   2.3\n"
    )
    _, tables = read_sar_text(_write(tmp_path, body))
    assert len(tables) == 1
    assert len(tables[0].rows) == 4
    assert [r.values["%usr"] for r in tables[0].rows] == [1.0, 1.1, 1.2, 1.3]


def test_Average行はデータ行に含まれない(tmp_path):
    body = (
        "\n"
        "00:00:02   CPU  %usr\n"
        "00:10:00   all   1.0\n"
        "\n"
        "Average:   CPU  %usr\n"
        "Average:   all   9.9\n"
    )
    _, tables = read_sar_text(_write(tmp_path, body))
    values = [r.values["%usr"] for t in tables for r in t.rows]
    assert values == [1.0]
    assert 9.9 not in values


def test_空行の直後は必ずヘッダ行として扱う(tmp_path):
    """データ行と同じ形をしたヘッダ行でも、空行の直後ならヘッダとして扱うこと。"""
    body = (
        "\n"
        "00:00:02   proc/s  cswch/s\n"
        "00:10:00     1.00     2.00\n"
        "\n"
        "00:10:00   pswpin/s  pswpout/s\n"
        "00:20:00       3.00       4.00\n"
    )
    _, tables = read_sar_text(_write(tmp_path, body))
    assert len(tables) == 2
    assert tables[0].columns == ["proc/s", "cswch/s"]
    assert tables[1].columns == ["pswpin/s", "pswpout/s"]


@pytest.mark.parametrize("label", ["CPU", "DEV", "IFACE", "TTY"])
def test_キー付きグループの判定(tmp_path, label):
    body = f"\n00:00:02   {label}  %util\n00:10:00   abc   1.0\n"
    _, tables = read_sar_text(_write(tmp_path, body))
    assert tables[0].key_label == label
    assert tables[0].columns == ["%util"]
    assert tables[0].rows[0].key == "abc"


def test_キーなしグループの判定(tmp_path):
    body = "\n00:00:02   proc/s  cswch/s\n00:10:00    1.0     2.0\n"
    _, tables = read_sar_text(_write(tmp_path, body))
    assert tables[0].key_label is None
    assert tables[0].rows[0].key is None


def test_数値化できない値はNoneになり行は捨てられない(tmp_path):
    body = "\n00:00:02   proc/s  cswch/s\n00:10:00      -      2.0\n"
    _, tables = read_sar_text(_write(tmp_path, body))
    row = tables[0].rows[0]
    assert row.values["proc/s"] is None
    assert row.values["cswch/s"] == 2.0


def test_列数が合わない行は読み飛ばされ他の行に影響しない(tmp_path):
    body = (
        "\n"
        "00:00:02   proc/s  cswch/s\n"
        "00:10:00      1.0\n"          # 列数不足
        "00:20:00      2.0     3.0\n"
    )
    _, tables = read_sar_text(_write(tmp_path, body))
    assert len(tables[0].rows) == 1
    assert tables[0].rows[0].values["proc/s"] == 2.0


def test_AMPM形式の時刻を受理する(tmp_path):
    body = (
        "\n"
        "12:00:00 AM   proc/s\n"
        "01:50:00 PM      1.0\n"
    )
    _, tables = read_sar_text(_write(tmp_path, body))
    assert tables[0].rows[0].timestamp == "2026-08-23T13:50:00"


def test_時刻が巻き戻ったら日付が進む(tmp_path):
    body = (
        "\n"
        "00:00:02   proc/s\n"
        "23:50:00      1.0\n"
        "00:10:00      2.0\n"
    )
    _, tables = read_sar_text(_write(tmp_path, body))
    stamps = [r.timestamp for r in tables[0].rows]
    assert stamps == ["2026-08-23T23:50:00", "2026-08-24T00:10:00"]


def test_セクションが変わっても日跨ぎと誤判定しない(tmp_path):
    """CPU セクションが 23:50 で終わり、次のセクションが 00:00 から始まる形。

    日跨ぎ判定をファイル全体で共有すると、ここで誤って日付が進む。
    """
    body = (
        "\n"
        "00:00:02   proc/s\n"
        "23:50:00      1.0\n"
        "\n"
        "00:00:02   pswpin/s\n"
        "00:10:00      2.0\n"
    )
    _, tables = read_sar_text(_write(tmp_path, body))
    second = [t for t in tables if t.columns == ["pswpin/s"]][0]
    assert second.rows[0].timestamp == "2026-08-23T00:10:00"
