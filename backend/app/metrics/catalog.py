"""メトリクスグループの定義と、sar 列名 / sadf キーからの判定 (docs/P003-backend-spec.md §9.3, §10).

本モジュールが唯一の定義元である。両リーダはここを参照し、独自の判定を持たない。
指標名は sar テキストの表記に揃える (sadf 側は SADF_FIELD_TO_METRIC で読み替える)。
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GroupDef:
    groupId: str
    title: str
    description: str
    keyLabel: str | None
    displayOrder: int
    # sar テキストでこのグループと判定するための識別列。
    # 「この列がすべて含まれていれば該当」とする。列の並び順・個数に依存しない。
    sarMarkers: tuple[str, ...] = field(default=())


# docs/P001-requirement.md §7 の一覧に対応する。displayOrder は同表の並び。
GROUP_DEFS: tuple[GroupDef, ...] = (
    GroupDef(
        "MG-CPU", "CPU 使用率",
        "CPU 時間の内訳。%iowait が高ければ I/O 待ち、%steal が高ければ仮想化基盤側での取られ待ちを疑う。",
        "CPU", 1, ("%usr",),
    ),
    GroupDef(
        "MG-PROC", "プロセス生成・コンテキストスイッチ",
        "1 秒あたりのプロセス生成数と、コンテキストスイッチ回数。",
        None, 2, ("proc/s",),
    ),
    GroupDef(
        "MG-SWPIO", "スワップイン / アウト",
        "1 秒あたりにスワップ領域と交換されたページ数。恒常的に発生していればメモリ不足を疑う。",
        None, 3, ("pswpin/s",),
    ),
    GroupDef(
        "MG-PAGE", "ページング",
        "メモリページの入出力とページフォールトの発生状況。",
        None, 4, ("pgpgin/s",),
    ),
    GroupDef(
        "MG-IO", "ブロック I/O (全体)",
        "システム全体の 1 秒あたり I/O 転送回数と転送ブロック数。",
        None, 5, ("tps", "bread/s"),
    ),
    GroupDef(
        "MG-MEM", "メモリ使用量",
        "物理メモリの使用状況。kbavail が実質的な空き容量を表す。",
        None, 6, ("kbmemfree",),
    ),
    GroupDef(
        "MG-SWAP", "スワップ使用量",
        "スワップ領域の使用状況。",
        None, 7, ("kbswpfree",),
    ),
    GroupDef(
        "MG-HUGE", "HugePages",
        "HugePages の割り当て状況。",
        None, 8, ("kbhugfree",),
    ),
    GroupDef(
        "MG-KTBL", "カーネルテーブル",
        "ファイルディスクリプタ・inode などカーネル内テーブルの使用数。",
        None, 9, ("dentunusd",),
    ),
    GroupDef(
        "MG-LOAD", "ロードアベレージ・実行キュー",
        "実行待ちタスク数とロードアベレージ。CPU 数を継続的に超えていれば過負荷を疑う。",
        None, 10, ("runq-sz",),
    ),
    GroupDef(
        "MG-TTY", "TTY デバイス",
        "シリアル端末の送受信・エラー発生状況。",
        "TTY", 11, ("rcvin/s",),
    ),
    GroupDef(
        "MG-DISK", "ブロックデバイス別 I/O",
        "デバイスごとの I/O 量と応答時間。%util が 100% に張り付けば飽和、await はレイテンシを表す。",
        "DEV", 12, ("tps", "%util"),
    ),
    GroupDef(
        "MG-NET", "ネットワーク I/O",
        "インタフェースごとの送受信パケット数・転送量。",
        "IFACE", 13, ("rxpck/s",),
    ),
    GroupDef(
        "MG-NETERR", "ネットワークエラー",
        "インタフェースごとのエラー・破棄パケット数。通常はすべて 0 になる。",
        "IFACE", 14, ("rxerr/s",),
    ),
    GroupDef(
        "MG-NFSC", "NFS クライアント",
        "NFS クライアントとしての RPC 発行状況。",
        None, 15, ("call/s",),
    ),
    GroupDef(
        "MG-NFSD", "NFS サーバ",
        "NFS サーバとしての RPC 受信状況。",
        None, 16, ("scall/s",),
    ),
    GroupDef(
        "MG-SOCK", "ソケット使用数",
        "使用中ソケット数。tcp-tw は TIME_WAIT 状態のソケット数を表す。",
        None, 17, ("totsck",),
    ),
    GroupDef(
        "MG-SOFTNET", "ソフトネット処理",
        "CPU ごとのネットワークパケットのソフト割り込み処理状況。",
        "CPU", 18, ("squeezd/s",),
    ),
    # --- 以下 3 グループは P102 (実装) 中に実データで発見したものである。
    # docs/P001-requirement.md §7 の当初の一覧 (18 グループ) には含まれていなかったが、
    # 実データ (sar15..sar23) に時系列データとして存在するため、REQ-F-012
    # 「格納されている時系列データが全てグラフ表示される」を満たすには必要である。
    # 経緯は docs/P103 のテスト記録および docs/P001-requirement.md §7 の注記を参照。
    GroupDef(
        "MG-PSI-CPU", "CPU 逼迫度 (PSI)",
        "CPU の奪い合いでタスクが待たされた時間の割合 (Pressure Stall Information)。"
        "10 秒 / 60 秒 / 300 秒の移動平均と、集計期間の値。値が大きいほど CPU が不足している。",
        None, 19, ("%scpu-10",),
    ),
    GroupDef(
        "MG-PSI-IO", "I/O 逼迫度 (PSI)",
        "I/O 待ちでタスクが停滞した時間の割合 (Pressure Stall Information)。"
        "%s... は一部のタスクが待たされた割合、%f... は全タスクが待たされた割合を表す。",
        None, 20, ("%sio-10",),
    ),
    GroupDef(
        "MG-PSI-MEM", "メモリ逼迫度 (PSI)",
        "メモリ不足でタスクが停滞した時間の割合 (Pressure Stall Information)。"
        "%s... は一部のタスクが待たされた割合、%f... は全タスクが待たされた割合を表す。",
        None, 21, ("%smem-10",),
    ),
)

GROUP_BY_ID: dict[str, GroupDef] = {g.groupId: g for g in GROUP_DEFS}

# キー列見出しとして扱う値。sar のヘッダ行の 2 列目がこれらなら「キー付き」と判定する。
KEY_LABELS: frozenset[str] = frozenset({"CPU", "DEV", "IFACE", "TTY"})


# --- 指標の説明 (docs/P002-frontend-spec.md §5.4 で返す) ---
# 網羅ではなく、意味の分かりにくい主要な指標に説明を与える。
# ここに無い指標は説明を空文字ではなく指標名から生成した既定文にする。
METRIC_DESCRIPTIONS: dict[str, str] = {
    "%usr": "ユーザー空間での実行時間の割合",
    "%nice": "nice 値を変更したプロセスのユーザー空間実行時間の割合",
    "%sys": "カーネル空間での実行時間の割合",
    "%iowait": "I/O 完了待ちでアイドルだった時間の割合",
    "%steal": "仮想化基盤の他ゲストに CPU を取られて待った時間の割合",
    "%irq": "ハードウェア割り込みの処理時間の割合",
    "%soft": "ソフトウェア割り込みの処理時間の割合",
    "%idle": "アイドル時間の割合",
    "proc/s": "1 秒あたりに生成されたプロセス数",
    "cswch/s": "1 秒あたりのコンテキストスイッチ回数",
    "pswpin/s": "1 秒あたりにスワップインされたページ数",
    "pswpout/s": "1 秒あたりにスワップアウトされたページ数",
    "fault/s": "1 秒あたりのページフォールト数",
    "majflt/s": "1 秒あたりのメジャーフォールト数 (ディスク I/O を伴う)",
    "tps": "1 秒あたりの I/O 転送回数",
    "bread/s": "1 秒あたりの読み取りブロック数",
    "bwrtn/s": "1 秒あたりの書き込みブロック数",
    "kbmemfree": "未使用の物理メモリ量",
    "kbavail": "新規プロセスが利用可能なメモリ量 (実質的な空き)",
    "kbmemused": "使用中の物理メモリ量",
    "%memused": "物理メモリの使用率",
    "kbbuffers": "バッファに使われているメモリ量",
    "kbcached": "ページキャッシュに使われているメモリ量",
    "kbdirty": "ディスクへの書き戻し待ちのメモリ量",
    "kbswpfree": "未使用のスワップ領域",
    "kbswpused": "使用中のスワップ領域",
    "%swpused": "スワップ領域の使用率",
    "runq-sz": "実行待ちのタスク数",
    "plist-sz": "タスクリスト上のタスク・スレッド総数",
    "ldavg-1": "過去 1 分のロードアベレージ",
    "ldavg-5": "過去 5 分のロードアベレージ",
    "ldavg-15": "過去 15 分のロードアベレージ",
    "blocked": "I/O 完了待ちでブロックされているタスク数",
    "await": "I/O 要求が発行されてから完了するまでの平均時間",
    "%util": "デバイスが I/O 要求を処理していた時間の割合 (飽和度)",
    "aqu-sz": "I/O キューの平均長",
    "areq-sz": "I/O 要求の平均サイズ",
    "rkB/s": "1 秒あたりの読み取り量",
    "wkB/s": "1 秒あたりの書き込み量",
    "rxpck/s": "1 秒あたりの受信パケット数",
    "txpck/s": "1 秒あたりの送信パケット数",
    "rxkB/s": "1 秒あたりの受信量",
    "txkB/s": "1 秒あたりの送信量",
    "%ifutil": "インタフェース帯域の使用率",
    "rxerr/s": "1 秒あたりの受信エラー数",
    "txerr/s": "1 秒あたりの送信エラー数",
    "rxdrop/s": "1 秒あたりの受信破棄パケット数",
    "txdrop/s": "1 秒あたりの送信破棄パケット数",
    "totsck": "使用中のソケット総数",
    "tcpsck": "使用中の TCP ソケット数",
    "udpsck": "使用中の UDP ソケット数",
    "tcp-tw": "TIME_WAIT 状態の TCP ソケット数",
    "dentunusd": "未使用のディレクトリキャッシュエントリ数",
    "file-nr": "使用中のファイルハンドル数",
    "inode-nr": "使用中の inode ハンドル数",
    "squeezd/s": "処理時間切れで打ち切られたソフト割り込み回数",
    "dropd/s": "1 秒あたりに破棄されたパケット数",
    "%scpu-10": "過去 10 秒で一部のタスクが CPU 待ちだった時間の割合",
    "%scpu-60": "過去 60 秒で一部のタスクが CPU 待ちだった時間の割合",
    "%scpu-300": "過去 300 秒で一部のタスクが CPU 待ちだった時間の割合",
    "%scpu": "集計期間で一部のタスクが CPU 待ちだった時間の割合",
    "%sio-10": "過去 10 秒で一部のタスクが I/O 待ちで停滞した時間の割合",
    "%sio-60": "過去 60 秒で一部のタスクが I/O 待ちで停滞した時間の割合",
    "%sio-300": "過去 300 秒で一部のタスクが I/O 待ちで停滞した時間の割合",
    "%sio": "集計期間で一部のタスクが I/O 待ちで停滞した時間の割合",
    "%fio-10": "過去 10 秒で全タスクが I/O 待ちで停滞した時間の割合",
    "%fio-60": "過去 60 秒で全タスクが I/O 待ちで停滞した時間の割合",
    "%fio-300": "過去 300 秒で全タスクが I/O 待ちで停滞した時間の割合",
    "%fio": "集計期間で全タスクが I/O 待ちで停滞した時間の割合",
    "%smem-10": "過去 10 秒で一部のタスクがメモリ不足で停滞した時間の割合",
    "%smem-60": "過去 60 秒で一部のタスクがメモリ不足で停滞した時間の割合",
    "%smem-300": "過去 300 秒で一部のタスクがメモリ不足で停滞した時間の割合",
    "%smem": "集計期間で一部のタスクがメモリ不足で停滞した時間の割合",
    "%fmem-10": "過去 10 秒で全タスクがメモリ不足で停滞した時間の割合",
    "%fmem-60": "過去 60 秒で全タスクがメモリ不足で停滞した時間の割合",
    "%fmem-300": "過去 300 秒で全タスクがメモリ不足で停滞した時間の割合",
    "%fmem": "集計期間で全タスクがメモリ不足で停滞した時間の割合",
}


def metric_description(name: str) -> str:
    return METRIC_DESCRIPTIONS.get(name, f"{name} の値")


def unit_for(column_name: str) -> str | None:
    """列名から単位を決める (docs/P003-backend-spec.md §10).

    判定順が重要。'%' と 'kb' の判定を '/s' より先に行う
    (例: '%vmeff' は '%'、'kbhugfree' は 'KB')。
    """
    name = column_name
    if name.startswith("%"):
        return "%"
    lowered = name.lower()
    if lowered.startswith("kb") and not lowered.endswith("kb/s"):
        return "KB"
    if name.endswith("kB/s"):
        return "KB/s"
    if name == "await":
        return "ms"
    if name.endswith("/s"):
        return "/s"
    return None


def identify_group_from_sar(columns: list[str], key_label: str | None) -> str | None:
    """sar の列名集合とキー列見出しから groupId を決める。

    列の並び順・個数に依存しない (sysstat のバージョンで列が増減しうるため)。
    判定できない場合は None を返す (呼び出し側で無視して警告ログに出す)。
    """
    col_set = set(columns)
    candidates = [
        g
        for g in GROUP_DEFS
        if g.keyLabel == key_label
        and g.sarMarkers
        and all(marker in col_set for marker in g.sarMarkers)
    ]
    if not candidates:
        return None
    # 識別列が多いものを優先する。MG-IO ('tps','bread/s') と MG-DISK ('tps','%util') は
    # keyLabel で分かれるが、将来の追加で曖昧になった場合に、より特定的な定義を選ぶため。
    candidates.sort(key=lambda g: (-len(g.sarMarkers), g.displayOrder))
    return candidates[0].groupId


# --- sadf -j の統計種別キー -> groupId (docs/P003-backend-spec.md §9.3) ---
# ネストするキーは 'network.net-dev' のようにドット区切りで表す。
#
# ★FIXME★ 本対応表は sysstat の公開仕様にもとづく記述であり、この開発環境には
# sadf が無いため実出力での確認ができていない (docs/ArchitectureHandbook.md §9-1)。
# sadf が使える環境での初回実行時に確認し、相違があればここを修正すること。
SADF_KEY_TO_GROUP: dict[str, str] = {
    "cpu-load": "MG-CPU",
    "cpu-load-all": "MG-CPU",
    "process-and-context-switch": "MG-PROC",
    "swap-pages": "MG-SWPIO",
    "paging": "MG-PAGE",
    "io": "MG-IO",
    "memory": "MG-MEM",
    "hugepages": "MG-HUGE",
    "kernel": "MG-KTBL",
    "queue": "MG-LOAD",
    "serial": "MG-TTY",
    "disk": "MG-DISK",
    "network.net-dev": "MG-NET",
    "network.net-edev": "MG-NETERR",
    "network.net-nfs": "MG-NFSC",
    "network.net-nfsd": "MG-NFSD",
    "network.net-sock": "MG-SOCK",
    "network.net-softnet": "MG-SOFTNET",
    # PSI (Pressure Stall Information)。sar テキストからは実データで確認できたが、
    # sadf 側のキー名は未確認である ★FIXME★
    "psi-cpu": "MG-PSI-CPU",
    "psi-io": "MG-PSI-IO",
    "psi-mem": "MG-PSI-MEM",
}

# sadf JSON のキー付き統計における、キー項目のフィールド名。
SADF_KEY_FIELD: dict[str, str] = {
    "cpu-load": "cpu",
    "cpu-load-all": "cpu",
    "serial": "line",
    "disk": "disk-device",
    "network.net-dev": "iface",
    "network.net-edev": "iface",
    "network.net-softnet": "cpu",
}

# sadf JSON のフィールド名 -> sar テキスト表記の指標名。
# 指標名を sar 表記に揃えることで、両経路の結果が一致する (REQ-F-024)。
# ★FIXME★ SADF_KEY_TO_GROUP と同じ理由で実出力未確認。
SADF_FIELD_TO_METRIC: dict[str, str] = {
    # cpu-load
    "user": "%usr",
    "nice": "%nice",
    "system": "%sys",
    "iowait": "%iowait",
    "steal": "%steal",
    "irq": "%irq",
    "soft": "%soft",
    "guest": "%guest",
    "gnice": "%gnice",
    "idle": "%idle",
    # process-and-context-switch
    "proc": "proc/s",
    "cswch": "cswch/s",
    # swap-pages
    "pswpin": "pswpin/s",
    "pswpout": "pswpout/s",
    # paging
    "pgpgin": "pgpgin/s",
    "pgpgout": "pgpgout/s",
    "fault": "fault/s",
    "majflt": "majflt/s",
    "pgfree": "pgfree/s",
    "pgscank": "pgscank/s",
    "pgscand": "pgscand/s",
    "pgsteal": "pgsteal/s",
    "vmeff-percent": "%vmeff",
    # io
    "tps": "tps",
    "rtps": "rtps",
    "wtps": "wtps",
    "dtps": "dtps",
    "bread": "bread/s",
    "bwrtn": "bwrtn/s",
    "bdscd": "bdscd/s",
    # memory
    "memfree": "kbmemfree",
    "avail": "kbavail",
    "memused": "kbmemused",
    "memused-percent": "%memused",
    "buffers": "kbbuffers",
    "cached": "kbcached",
    "commit": "kbcommit",
    "commit-percent": "%commit",
    "active": "kbactive",
    "inactive": "kbinact",
    "dirty": "kbdirty",
    "anonpg": "kbanonpg",
    "slab": "kbslab",
    "kstack": "kbkstack",
    "pgtbl": "kbpgtbl",
    "vmused": "kbvmused",
    # hugepages
    "hugfree": "kbhugfree",
    "hugused": "kbhugused",
    "hugused-percent": "%hugused",
    "hugrsvd": "kbhugrsvd",
    "hugsurp": "kbhugsurp",
    # kernel
    "dentunusd": "dentunusd",
    "file-nr": "file-nr",
    "inode-nr": "inode-nr",
    "pty-nr": "pty-nr",
    # queue
    "runq-sz": "runq-sz",
    "plist-sz": "plist-sz",
    "ldavg-1": "ldavg-1",
    "ldavg-5": "ldavg-5",
    "ldavg-15": "ldavg-15",
    "blocked": "blocked",
    # serial
    "rcvin": "rcvin/s",
    "xmtin": "xmtin/s",
    "framerr": "framerr/s",
    "prtyerr": "prtyerr/s",
    "brk": "brk/s",
    "ovrun": "ovrun/s",
    # disk
    "rkB": "rkB/s",
    "wkB": "wkB/s",
    "dkB": "dkB/s",
    "areq-sz": "areq-sz",
    "aqu-sz": "aqu-sz",
    "await": "await",
    "util-percent": "%util",
    # net-dev
    "rxpck": "rxpck/s",
    "txpck": "txpck/s",
    "rxkB": "rxkB/s",
    "txkB": "txkB/s",
    "rxcmp": "rxcmp/s",
    "txcmp": "txcmp/s",
    "rxmcst": "rxmcst/s",
    "ifutil-percent": "%ifutil",
    # net-edev
    "rxerr": "rxerr/s",
    "txerr": "txerr/s",
    "coll": "coll/s",
    "rxdrop": "rxdrop/s",
    "txdrop": "txdrop/s",
    "txcarr": "txcarr/s",
    "rxfram": "rxfram/s",
    "rxfifo": "rxfifo/s",
    "txfifo": "txfifo/s",
    # net-nfs
    "call": "call/s",
    "retrans": "retrans/s",
    "read": "read/s",
    "write": "write/s",
    "access": "access/s",
    "getatt": "getatt/s",
    # net-nfsd
    "scall": "scall/s",
    "badcall": "badcall/s",
    "packet": "packet/s",
    "udp": "udp/s",
    "tcp": "tcp/s",
    "hit": "hit/s",
    "miss": "miss/s",
    "sread": "sread/s",
    "swrite": "swrite/s",
    "saccess": "saccess/s",
    "sgetatt": "sgetatt/s",
    # net-sock
    "totsck": "totsck",
    "tcpsck": "tcpsck",
    "udpsck": "udpsck",
    "rawsck": "rawsck",
    "ip-frag": "ip-frag",
    "tcp-tw": "tcp-tw",
    # net-softnet
    "total": "total/s",
    "dropd": "dropd/s",
    "squeezd": "squeezd/s",
    "rx_rps": "rx_rps/s",
    "flw_lim": "flw_lim/s",
    "blg_len": "blg_len",
    # psi-* (★FIXME★ sadf 側のフィールド名は未確認)
    "some-cpu-10": "%scpu-10",
    "some-cpu-60": "%scpu-60",
    "some-cpu-300": "%scpu-300",
    "some-cpu": "%scpu",
    "some-io-10": "%sio-10",
    "some-io-60": "%sio-60",
    "some-io-300": "%sio-300",
    "some-io": "%sio",
    "full-io-10": "%fio-10",
    "full-io-60": "%fio-60",
    "full-io-300": "%fio-300",
    "full-io": "%fio",
    "some-mem-10": "%smem-10",
    "some-mem-60": "%smem-60",
    "some-mem-300": "%smem-300",
    "some-mem": "%smem",
    "full-mem-10": "%fmem-10",
    "full-mem-60": "%fmem-60",
    "full-mem-300": "%fmem-300",
    "full-mem": "%fmem",
}

# MG-SWAP は sadf では memory キーの中に swap 系フィールドとして同居する可能性がある
# (docs/P003-backend-spec.md §15 #1)。sar 側の指標名で該当するものを列挙し、
# memory から切り出せるようにする。
SWAP_METRICS: frozenset[str] = frozenset(
    {"kbswpfree", "kbswpused", "%swpused", "kbswpcad", "%swpcad"}
)
SADF_FIELD_TO_METRIC.update(
    {
        "swpfree": "kbswpfree",
        "swpused": "kbswpused",
        "swpused-percent": "%swpused",
        "swpcad": "kbswpcad",
        "swpcad-percent": "%swpcad",
    }
)
