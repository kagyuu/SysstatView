"""両リーダが共通で返す中間表現 (docs/P003-backend-spec.md §7.2).

この中間表現を挟むことで、sa 経路と sar 経路の差異がリーダ層の内部に閉じ込められ、
「両経路の結果が一致すること」(REQ-F-024) が構造として担保される。
API には露出しないため Pydantic ではなく dataclass とする。
"""

from dataclasses import dataclass, field
from datetime import date


@dataclass
class RawRow:
    timestamp: str  # "YYYY-MM-DDTHH:mm:ss"
    key: str | None  # "all" / "vda" / "ens3" / None
    values: dict[str, float | None]  # 列名 -> 値


@dataclass
class RawTable:
    columns: list[str]  # キー列を除く列名
    key_label: str | None  # "CPU" / "DEV" / "IFACE" / "TTY" / None
    rows: list[RawRow] = field(default_factory=list)


@dataclass
class SarHeader:
    """ログファイルの先頭から得られる採取元の情報。"""

    date: date
    hostname: str | None = None
    kernel: str | None = None
    arch: str | None = None
    cpu_count: int | None = None
