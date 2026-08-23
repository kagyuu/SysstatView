"""GET /api/metric-catalog (docs/P002-frontend-spec.md §5.4)."""

from fastapi import APIRouter

from app.metrics.catalog import (
    GROUP_DEFS,
    METRIC_DESCRIPTIONS,
    metric_description,
    unit_for,
)
from app.models import GroupDefInfo, MetricCatalogResponse, MetricDefInfo

router = APIRouter(prefix="/api", tags=["catalog"])

# グループごとの指標一覧は、説明表と識別列から導ける範囲で構成する。
# 実データに現れる列は sar/sadf のバージョンで増減しうるため、ここでは
# 「説明を用意してある指標」を列挙し、画面はメトリクス応答側の series を正とする。
_GROUP_METRIC_HINTS: dict[str, tuple[str, ...]] = {
    "MG-CPU": ("%usr", "%nice", "%sys", "%iowait", "%steal", "%irq", "%soft", "%guest", "%gnice", "%idle"),
    "MG-PROC": ("proc/s", "cswch/s"),
    "MG-SWPIO": ("pswpin/s", "pswpout/s"),
    "MG-PAGE": ("pgpgin/s", "pgpgout/s", "fault/s", "majflt/s", "pgfree/s", "pgscank/s", "pgscand/s", "pgsteal/s", "%vmeff"),
    "MG-IO": ("tps", "rtps", "wtps", "dtps", "bread/s", "bwrtn/s", "bdscd/s"),
    "MG-MEM": ("kbmemfree", "kbavail", "kbmemused", "%memused", "kbbuffers", "kbcached", "kbcommit", "%commit", "kbactive", "kbinact", "kbdirty", "kbanonpg", "kbslab", "kbkstack", "kbpgtbl", "kbvmused"),
    "MG-SWAP": ("kbswpfree", "kbswpused", "%swpused", "kbswpcad", "%swpcad"),
    "MG-HUGE": ("kbhugfree", "kbhugused", "%hugused", "kbhugrsvd", "kbhugsurp"),
    "MG-KTBL": ("dentunusd", "file-nr", "inode-nr", "pty-nr"),
    "MG-LOAD": ("runq-sz", "plist-sz", "ldavg-1", "ldavg-5", "ldavg-15", "blocked"),
    "MG-TTY": ("rcvin/s", "xmtin/s", "framerr/s", "prtyerr/s", "brk/s", "ovrun/s"),
    "MG-DISK": ("tps", "rkB/s", "wkB/s", "dkB/s", "areq-sz", "aqu-sz", "await", "%util"),
    "MG-NET": ("rxpck/s", "txpck/s", "rxkB/s", "txkB/s", "rxcmp/s", "txcmp/s", "rxmcst/s", "%ifutil"),
    "MG-NETERR": ("rxerr/s", "txerr/s", "coll/s", "rxdrop/s", "txdrop/s", "txcarr/s", "rxfram/s", "rxfifo/s", "txfifo/s"),
    "MG-NFSC": ("call/s", "retrans/s", "read/s", "write/s", "access/s", "getatt/s"),
    "MG-NFSD": ("scall/s", "badcall/s", "packet/s", "udp/s", "tcp/s", "hit/s", "miss/s", "sread/s", "swrite/s", "saccess/s", "sgetatt/s"),
    "MG-SOCK": ("totsck", "tcpsck", "udpsck", "rawsck", "ip-frag", "tcp-tw"),
    "MG-SOFTNET": ("total/s", "dropd/s", "squeezd/s", "rx_rps/s", "flw_lim/s", "blg_len"),
    "MG-PSI-CPU": ("%scpu-10", "%scpu-60", "%scpu-300", "%scpu"),
    "MG-PSI-IO": ("%sio-10", "%sio-60", "%sio-300", "%sio", "%fio-10", "%fio-60", "%fio-300", "%fio"),
    "MG-PSI-MEM": ("%smem-10", "%smem-60", "%smem-300", "%smem", "%fmem-10", "%fmem-60", "%fmem-300", "%fmem"),
}


@router.get("/metric-catalog", response_model=MetricCatalogResponse)
def get_metric_catalog() -> MetricCatalogResponse:
    groups = [
        GroupDefInfo(
            groupId=g.groupId,
            title=g.title,
            description=g.description,
            keyLabel=g.keyLabel,
            metrics=[
                MetricDefInfo(
                    name=name,
                    unit=unit_for(name),
                    description=metric_description(name),
                )
                for name in _GROUP_METRIC_HINTS.get(g.groupId, ())
            ],
        )
        for g in sorted(GROUP_DEFS, key=lambda x: x.displayOrder)
    ]
    return MetricCatalogResponse(groups=groups)
