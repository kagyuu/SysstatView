"""U005-T1 — fileId の生成と解決 (ADR-007)."""
import base64
import os
import pytest

from app.errors import FileNotFoundAppError
from app.services.catalog_service import encode_file_id
from app.services.metrics_service import resolve_file_id


def _fid(name: str) -> str:
    return base64.urlsafe_b64encode(name.encode()).decode().rstrip("=")


def test_生成と解決の往復(real_log_dir):
    path = resolve_file_id(encode_file_id("sar23"), real_log_dir)
    assert path.name == "sar23"


@pytest.mark.parametrize(
    "name",
    ["../../etc/passwd", "/etc/passwd", r"..\..\windows\win.ini",
     "README.md", "sa1", "sa123", "saXX", "sar23x", "", "sa99"],
)
def test_不正または存在しない名前はすべて404(real_log_dir, name):
    with pytest.raises(FileNotFoundAppError):
        resolve_file_id(_fid(name), real_log_dir)


def test_base64として不正な文字列は404(real_log_dir):
    with pytest.raises(FileNotFoundAppError):
        resolve_file_id("notbase64!!!", real_log_dir)


def test_ディレクトリ外を指すシンボリックリンクは404(copied_log_dir, tmp_path):
    outside = tmp_path / "outside.txt"
    outside.write_text("secret", encoding="utf-8")
    link = copied_log_dir / "sa77"
    try:
        os.symlink(outside, link)
    except (OSError, NotImplementedError):
        pytest.skip("この環境ではシンボリックリンクを作成できない")
    with pytest.raises(FileNotFoundAppError):
        resolve_file_id(_fid("sa77"), copied_log_dir)
