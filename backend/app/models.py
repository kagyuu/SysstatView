"""API 応答の Pydantic モデル (docs/P003-backend-spec.md §4.2).

フィールド名は camelCase で直接定義する (alias を使わない)。
docs/P002-frontend-spec.md §5 の応答例と 1 対 1 に対応させる。
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel

Kind = Literal["sa", "sar"]


class LogFileInfo(BaseModel):
    """一覧の 1 行 (docs/P002-frontend-spec.md §5.2)."""

    fileId: str
    fileName: str
    kind: Kind
    date: date
    sizeBytes: int
    hostname: str | None = None


class LogFileListResponse(BaseModel):
    page: int
    perPage: int
    totalItems: int
    totalPages: int
    items: list[LogFileInfo]


class Series(BaseModel):
    """1 系列。values の長さは属するグループの timestamps と必ず一致する (INV-1)."""

    key: str | None
    metric: str
    unit: str | None
    values: list[float | None]


class MetricGroup(BaseModel):
    groupId: str
    keyLabel: str | None
    timestamps: list[str]
    series: list[Series]


class MetricsResponse(BaseModel):
    """docs/P002-frontend-spec.md §5.3. kind によらず同一スキーマ (REQ-F-024)."""

    fileId: str
    fileName: str
    kind: Kind
    date: date
    hostname: str | None
    kernel: str | None
    arch: str | None
    cpuCount: int | None
    groups: list[MetricGroup]


class MetricDefInfo(BaseModel):
    name: str
    unit: str | None
    description: str


class GroupDefInfo(BaseModel):
    groupId: str
    title: str
    description: str
    keyLabel: str | None
    metrics: list[MetricDefInfo]


class MetricCatalogResponse(BaseModel):
    groups: list[GroupDefInfo]


class HealthResponse(BaseModel):
    """docs/P002-frontend-spec.md §5.5.

    sadfAvailable が False でも status は "ok" のまま返す (REQ-N-015)。
    """

    status: str
    logDir: str
    sadfAvailable: bool
    sadfVersion: str | None
    readableFileCount: int
    unreadableFileCount: int


class ErrorBody(BaseModel):
    code: str
    message: str
    detail: str | None = None
    hint: str | None = None


class ErrorResponse(BaseModel):
    error: ErrorBody
