# SysstatView バックエンド (docs/P007-impl-direction/U008-containerization.md)
FROM python:3.12-slim

# sa バイナリの読み取りに sadf が必要 (REQ-N-011 / ADR-002)。
RUN apt-get update \
 && apt-get install -y --no-install-recommends sysstat \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 依存を先に入れてレイヤキャッシュを効かせる。
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# 非 root で実行する。
RUN useradd --create-home --uid 10001 appuser
USER appuser

ENV SYSSTAT_LOG_DIR=/var/log/sysstat \
    PYTHONUNBUFFERED=1

EXPOSE 8000

# ワーカー数 2 (docs/P005-impl-plan.md §3 U008 の決定 / REQ-N-012)。
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
