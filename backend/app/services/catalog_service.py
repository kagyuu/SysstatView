"""ログディレクトリの走査・採取日の解決・キャッシュ・期間フィルタ・ページング
(docs/P003-backend-spec.md §6).
"""

import base64
import logging
import math
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.errors import AppError, InvalidParameterError
from app.logging_setup import log_event
from app.models import LogFileInfo
from app.readers import sa_binary, sar_text

# 対象とするファイル名。sar は 'sar' + 2 桁、sa は 'sa' + 2 桁。
LOG_FILE_NAME_RE = re.compile(r"^sar?[0-9]{2}$")

MAX_PER_PAGE = 100


@dataclass
class CatalogEntry:
    """docs/P002-frontend-spec.md §6.3 / docs/P003-backend-spec.md §4.3.

    abs_path は API 応答に含めない。
    """

    file_id: str
    file_name: str
    kind: str
    abs_path: Path
    size_bytes: int
    mtime_ns: int
    date: date | None
    hostname: str | None


def encode_file_id(file_name: str) -> str:
    """base64url、パディング '=' を除去 (docs/P003-backend-spec.md §5.1)."""
    return base64.urlsafe_b64encode(file_name.encode("utf-8")).decode("ascii").rstrip("=")


def decode_file_id(file_id: str) -> str | None:
    padding = "=" * (-len(file_id) % 4)
    try:
        return base64.urlsafe_b64decode(file_id + padding).decode("utf-8")
    except Exception:
        return None


def kind_of(file_name: str) -> str:
    # 判定順が重要。'sar23' を 'sa' と誤判定しないよう sar を先に見る。
    return "sar" if file_name.startswith("sar") else "sa"


class CatalogService:
    """プロセス内メモリのキャッシュを持つ (ADR-004)。

    キャッシュの失効は (絶対パス, mtime, サイズ) の一致で判定する。
    時間ベースの有効期限は設けない。
    """

    def __init__(self) -> None:
        # 絶対パス -> (mtime_ns, size, CatalogEntry)
        self._cache: dict[str, tuple[int, int, CatalogEntry]] = {}

    def clear(self) -> None:
        self._cache.clear()

    # --- 走査 ---

    def scan(self, log_dir: Path) -> list[CatalogEntry]:
        """ログディレクトリ直下を走査し、採取日を解決したエントリを返す。

        採取日を取得できなかったものは date=None のまま含める
        (件数を health で見せるため)。一覧からは呼び出し側が除外する。
        """
        entries: list[CatalogEntry] = []
        if not log_dir.is_dir():
            return entries
        try:
            candidates = sorted(log_dir.iterdir(), key=lambda p: p.name)
        except OSError:
            return entries

        for path in candidates:
            if not LOG_FILE_NAME_RE.match(path.name):
                continue
            try:
                if not path.is_file():
                    continue
                # シンボリックリンクがディレクトリ外を指す場合を除外する。
                resolved = path.resolve()
                if resolved.parent != log_dir.resolve():
                    continue
                stat = path.stat()
            except OSError:
                continue
            entries.append(self._resolve_entry(path, stat.st_mtime_ns, stat.st_size))
        return entries

    def _resolve_entry(self, path: Path, mtime_ns: int, size: int) -> CatalogEntry:
        abs_key = str(path.resolve())
        cached = self._cache.get(abs_key)
        if cached is not None and cached[0] == mtime_ns and cached[1] == size:
            return cached[2]

        file_name = path.name
        kind = kind_of(file_name)
        entry_date: date | None = None
        hostname: str | None = None
        try:
            if kind == "sar":
                header = sar_text.read_header(path)
            else:
                header = sa_binary.read_sa_date(path)
            entry_date = header.date
            hostname = header.hostname
        except AppError as exc:
            # sadf が無い環境で sa が読めないのは正常な状態である (REQ-N-015)。
            log_event(
                logging.INFO if kind == "sa" else logging.WARNING,
                "reader.failed",
                "採取日を取得できませんでした。",
                fileName=file_name,
                reason=exc.code,
            )
        except Exception as exc:  # 想定外でも一覧全体を壊さない
            log_event(
                logging.WARNING,
                "reader.failed",
                "採取日の取得中に想定外のエラーが発生しました。",
                fileName=file_name,
                reason=type(exc).__name__,
            )

        entry = CatalogEntry(
            file_id=encode_file_id(file_name),
            file_name=file_name,
            kind=kind,
            abs_path=path,
            size_bytes=size,
            mtime_ns=mtime_ns,
            date=entry_date,
            hostname=hostname,
        )
        self._cache[abs_key] = (mtime_ns, size, entry)
        return entry

    # --- 一覧 ---

    def readable(self, log_dir: Path) -> list[CatalogEntry]:
        return [e for e in self.scan(log_dir) if e.date is not None]

    def counts(self, log_dir: Path) -> tuple[int, int]:
        entries = self.scan(log_dir)
        readable = sum(1 for e in entries if e.date is not None)
        return readable, len(entries) - readable

    def find_by_date_and_kind(
        self, log_dir: Path, target: date, kind: str
    ) -> CatalogEntry | None:
        for entry in self.readable(log_dir):
            if entry.date == target and entry.kind == kind:
                return entry
        return None

    def list_page(
        self, log_dir: Path, date_from: date, date_to: date, page: int, per_page: int
    ) -> tuple[list[LogFileInfo], int, int]:
        """期間フィルタ -> ソート -> ページ切り出し (docs/P003-backend-spec.md §6.3)."""
        selected = [
            e for e in self.readable(log_dir) if date_from <= e.date <= date_to
        ]
        # 採取日昇順 -> 同一日は sa -> sar -> ファイル名昇順
        selected.sort(key=lambda e: (e.date, 0 if e.kind == "sa" else 1, e.file_name))

        total_items = len(selected)
        total_pages = math.ceil(total_items / per_page) if total_items else 0
        start = (page - 1) * per_page
        window = selected[start : start + per_page]
        items = [
            LogFileInfo(
                fileId=e.file_id,
                fileName=e.file_name,
                kind=e.kind,
                date=e.date,
                sizeBytes=e.size_bytes,
                hostname=e.hostname,
            )
            for e in window
        ]
        return items, total_items, total_pages


def parse_date_param(value: str, name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except (ValueError, TypeError) as exc:
        raise InvalidParameterError(
            f"{name} は YYYY-MM-DD 形式で指定してください。",
            detail=f"{name}={value!r}",
        ) from exc


def validate_paging(page: int, per_page: int) -> None:
    if page < 1:
        raise InvalidParameterError("page は 1 以上で指定してください。", detail=f"page={page}")
    if per_page < 1 or per_page > MAX_PER_PAGE:
        raise InvalidParameterError(
            f"perPage は 1〜{MAX_PER_PAGE} で指定してください。", detail=f"perPage={per_page}"
        )


_service = CatalogService()


def get_catalog_service() -> CatalogService:
    return _service
