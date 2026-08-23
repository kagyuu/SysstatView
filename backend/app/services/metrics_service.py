"""fileId の解決とメトリクス取得 (docs/P003-backend-spec.md §5, §7 / ADR-007)."""

from collections import OrderedDict
from pathlib import Path

from app.errors import FileNotFoundAppError, SadfFailedError, SadfUnavailableError
from app.models import MetricsResponse
from app.readers import sa_binary, sar_text
from app.readers.normalize import normalize
from app.services.catalog_service import (
    LOG_FILE_NAME_RE,
    CatalogService,
    decode_file_id,
    kind_of,
)

CACHE_MAX_ENTRIES = 8


def resolve_file_id(file_id: str, log_dir: Path) -> Path:
    """docs/P003-backend-spec.md §5.2 のフロー。

    検証順序を変えてはならない。正規表現による検証をパス結合より前に行うことで、
    '../' や絶対パスを含む入力がパス操作に到達しない。
    失敗はすべて FileNotFoundAppError (404) に丸め、存在の有無を区別させない。
    """
    not_found = FileNotFoundAppError("指定されたログファイルが見つかりません。")

    # 1. base64url として復号できるか
    file_name = decode_file_id(file_id)
    if file_name is None:
        raise not_found

    # 2. 命名規則に合致するか (パス結合より前に行う)
    if not LOG_FILE_NAME_RE.match(file_name):
        raise not_found

    # 3. ログディレクトリと結合
    candidate = log_dir / file_name

    # 4. realpath がログディレクトリ直下か
    try:
        resolved = candidate.resolve()
        if resolved.parent != log_dir.resolve():
            raise not_found
        # 5. 通常ファイルとして存在するか
        if not resolved.is_file():
            raise not_found
    except OSError as exc:
        raise not_found from exc

    return candidate


class MetricsService:
    def __init__(self) -> None:
        # (絶対パス, mtime_ns, size) -> MetricsResponse の LRU
        self._cache: OrderedDict[tuple[str, int, int], MetricsResponse] = OrderedDict()

    def clear(self) -> None:
        self._cache.clear()

    def get_metrics(
        self, file_id: str, log_dir: Path, catalog: CatalogService
    ) -> MetricsResponse:
        path = resolve_file_id(file_id, log_dir)
        try:
            stat = path.stat()
        except OSError as exc:
            raise FileNotFoundAppError("指定されたログファイルが見つかりません。") from exc

        cache_key = (str(path.resolve()), stat.st_mtime_ns, stat.st_size)
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._cache.move_to_end(cache_key)
            return cached

        file_name = path.name
        kind = kind_of(file_name)
        try:
            if kind == "sar":
                header, tables = sar_text.read_sar_text(path)
            else:
                header, tables = sa_binary.read_sa_binary(path)
        except (SadfUnavailableError, SadfFailedError) as exc:
            # 同一採取日の sar があれば案内する (docs/P003-backend-spec.md §11.2)。
            exc.hint = self._sar_fallback_hint(path, log_dir, catalog)
            raise

        groups = normalize(tables, file_name=file_name)
        response = MetricsResponse(
            fileId=file_id,
            fileName=file_name,
            kind=kind,
            date=header.date,
            hostname=header.hostname,
            kernel=header.kernel,
            arch=header.arch,
            cpuCount=header.cpu_count,
            groups=groups,
        )

        self._cache[cache_key] = response
        self._cache.move_to_end(cache_key)
        while len(self._cache) > CACHE_MAX_ENTRIES:
            self._cache.popitem(last=False)
        return response

    @staticmethod
    def _sar_fallback_hint(
        path: Path, log_dir: Path, catalog: CatalogService
    ) -> str | None:
        # sa ファイルの採取日はまさに読めなかったので、ファイル名の日 (DD) を手掛かりに
        # 同名の sar を探す。sar 側は 1 行目から採取日を読めるため、そこで日を照合する。
        day_suffix = path.name[2:]
        sar_name = f"sar{day_suffix}"
        for entry in catalog.readable(log_dir):
            if entry.file_name == sar_name:
                return (
                    f"同一日の sar ファイル ({sar_name}) が存在します。"
                    "そちらを選択すると閲覧できます。"
                )
        return None


_service = MetricsService()


def get_metrics_service() -> MetricsService:
    return _service
