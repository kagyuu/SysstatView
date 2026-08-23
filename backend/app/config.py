"""アプリケーション設定 (docs/P003-backend-spec.md §6.1)."""

import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_LOG_DIR = "/var/log/sysstat"


@dataclass(frozen=True)
class Settings:
    """実行時設定。環境変数から組み立てる。"""

    log_dir: Path

    @property
    def log_dir_str(self) -> str:
        return str(self.log_dir)


def get_settings() -> Settings:
    """設定を返す。

    モジュール変数ではなく関数で返すのは、テストから環境変数を差し替えた際に
    その変更が反映されるようにするため (docs/P007-impl-direction/U001 T1)。
    """
    return Settings(log_dir=Path(os.environ.get("SYSSTAT_LOG_DIR", DEFAULT_LOG_DIR)))
