# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project status

Pre-implementation. The repository currently contains only `README.md` ("Visualize sysstat log"), two empty
placeholder `require.txt` files, and an untracked `sysstat-log/` sample data set. There is no build system,
no dependency manifest, no tests, and no source code yet — so there are no build/lint/test commands to run.
Do not invent them; when the first code lands, choose the stack explicitly with the user and record the
real commands here.

Only `README.md` is tracked by git. `require.txt` / `require - コピー.txt` are 0 bytes — they are intended
as a requirements document, not a Python `requirements.txt`.

## Sample data: `sysstat-log/`

Mirrors a Linux host's `/var/log/sysstat/` path (`sysstat-log/var/log/sysstat/`), captured from an
Ubuntu host `www4250uj` (kernel 6.8.0, x86_64, 3 CPUs) over 2026-08-15..24. ~15 MB, untracked — treat it
as fixture input for the viewer, and keep it out of commits unless the user asks otherwise.

Two file families live side by side and are **not** interchangeable:

- `saDD` — sysstat's binary daily archive (little-endian magic `96 d5 75 21`). Version- and
  architecture-sensitive; only readable via the `sysstat` toolchain (`sar -f saDD`, or
  `sadf -j/-x/-c saDD` for JSON/XML/CSV). Not parseable directly, and not readable on Windows without
  a Linux/WSL sysstat install.
- `sarDD` — the plain-text daily report (`sar -A` output), produced by cron the following morning.
  This is the practical parsing target.

`DD` is the day-of-month the data covers, so a full set wraps monthly. `sa24` exists without a matching
`sar24`: the text report for the current day is only generated after midnight, so the parser must tolerate
a binary-only (partial, in-progress) day.

### `sarDD` text format — parsing notes

```
Linux 6.8.0-106-generic (www4250uj) 	2026-08-23 	_x86_64_	(3 CPU)
<blank>
00:00:02        CPU      %usr     %nice ...        <- section header (metric names)
00:10:09        all      2.07      0.02 ...        <- sample rows, ~10 min interval
...
Average:         0.08      0.07 ...                <- section footer
<blank>
```

Gotchas that shape any parser:

- Line 1 is the only place the **date** appears; every data row carries a time only. Rows must be joined
  to the file's date, and the file's own name is the more reliable day key.
- Blank lines separate sections; a section is identified by its header row's column names, not by position.
- **Headers repeat mid-section.** For multi-row sections (per-CPU, per-device, per-interface) sar re-emits
  the header roughly every 13 samples. A parser that assumes one header per section will misread data rows
  as headers and vice versa.
- Multi-row sections key each sample by the second column (`all`/`0`/`1`/`2` for CPU, device name for `DEV`,
  interface name for `IFACE`). The set of keys varies per host and can be large — this sample has ~30
  interfaces (`ens*`, `docker0`, many `br-*` and `veth*` from Docker).
- `Average:` rows must be skipped (or handled separately) — they are aggregates, not samples.
- Columns are whitespace-aligned, not fixed-width; split on runs of whitespace.
- Sample timestamps drift (00:10:09, 00:20:12, 00:30:03) — intervals are approximate, so charts should plot
  against actual timestamps rather than assume a fixed grid.
- Locale affects the time column (this sample is 24-hour `HH:MM:SS`; `LC_TIME` can produce `HH:MM:SS AM/PM`
  and shift column offsets).

Sections present in the sample, in file order: CPU utilization, `proc/s cswch/s`, swap paging, paging,
block I/O (`tps`), memory (`kbmemfree`…), swap usage, hugepages, kernel tables (`dentunusd`…), load/run
queue (`runq-sz`, `ldavg-*`), TTY, per-device disk (`DEV`), per-interface network (`IFACE`, twice — traffic
then errors), NFS client (`call/s`), NFS server (`scall/s`), sockets (`totsck`), and softnet per-CPU.
