# backend/ 実装構造の目次

FastAPI バックエンド。sysstat の `saDD` / `sarDD` を読み、時系列メトリクスを JSON で返す。

* 設計: `docs/P003-backend-spec.md` / 決定の理由: `docs/ADR.md`
* 起動: `SYSSTAT_LOG_DIR=<ログディレクトリ> python -m uvicorn app.main:app --port 8000`
* テスト: `python -m pytest tests -q` (backend/ をカレントにして実行)

## アプリケーション

| パス | 概要 |
| --- | --- |
| `app/main.py` | FastAPI アプリ生成。例外→エラー応答の変換ハンドラとリクエストログのミドルウェアを登録する。CORS は入れない (ADR-001) |
| `app/config.py` | `SYSSTAT_LOG_DIR` の読み取り。テストから差し替えられるよう関数で返す |
| `app/models.py` | API 応答の Pydantic モデル。フィールド名は camelCase |
| `app/errors.py` | ドメイン例外 `AppError` 階層。リーダ層・サービス層はこれだけを投げる |
| `app/logging_setup.py` | 標準出力への 1 行 1 JSON ログ |

## ルータ (HTTP の入出力)

| パス | 概要 |
| --- | --- |
| `app/routers/health.py` | `GET /api/health`。`sadf` の可否と読み取り可能ファイル数を返す |
| `app/routers/log_files.py` | `GET /api/log-files` (一覧) と `GET /api/log-files/{fileId}/metrics` (時系列) |
| `app/routers/catalog.py` | `GET /api/metric-catalog`。グループの表示名・説明・指標定義 |

## サービス (業務ロジック)

| パス | 概要 |
| --- | --- |
| `app/services/catalog_service.py` | ログディレクトリ走査、採取日の解決とキャッシュ、期間フィルタ・ソート・ページング、`fileId` の生成 |
| `app/services/metrics_service.py` | `fileId` の解決 (パストラバーサル防止。ADR-007)、リーダ選択、LRU キャッシュ、`sa` 失敗時の `sar` 誘導 hint |

## リーダ (ファイル読み取り)

| パス | 概要 |
| --- | --- |
| `app/readers/raw.py` | 両経路が共通で返す中間表現 `RawTable` / `RawRow` / `SarHeader` |
| `app/readers/sar_text.py` | `sar` テキストの解析。**空行区切りのブロックを列構成ごとに連結する**のが要点 (ADR-003) |
| `app/readers/sa_binary.py` | `sadf -j -- -A` の起動と JSON の解釈 (ADR-002)。実 `sadf` での確認は未実施 |
| `app/readers/normalize.py` | 中間表現 → API 応答への正規化と不変条件 INV-1〜5 の検証。**両経路が必ずここを通る** |

## メトリクス定義

| パス | 概要 |
| --- | --- |
| `app/metrics/catalog.py` | 21 メトリクスグループの定義、単位割り当て規則、`sar` 列名 / `sadf` キーからの判定表。**定義の唯一の置き場** |

## テスト

| パス | 概要 |
| --- | --- |
| `tests/conftest.py` | 実データ / コピー / TestClient の fixture。キャッシュのリセット |
| `tests/test_sar_text.py` | `sar` 解析の落とし穴 (繰り返しヘッダ・`Average:`・AM/PM・日跨ぎ) を合成データで検証 |
| `tests/test_sar_realdata.py` | 実データ `sar15`〜`sar23` を通した検証 |
| `tests/test_sa_binary.py` | `sadf` 起動のモックとフィクスチャによる `sa` 経路の検証 |
| `tests/test_normalize.py` | 連結・欠損補完・INV 違反検出 |
| `tests/test_fileid.py` | パストラバーサル防止 |
| `tests/test_catalog_scan.py` / `test_catalog_def.py` | 走査・採取日・キャッシュ / グループ定義 |
| `tests/test_log_files_api.py` / `test_metrics_api.py` / `test_health.py` / `test_models.py` / `test_errors.py` / `test_config.py` | API と基盤 |
| `tests/integration/test_t001..t006*.py` | 結合テスト (`docs/P008-test-direction.md` の T001〜T006) |
| `tests/acceptance/test_a002..a004*.py` | 受け入れテスト (`docs/P009-acceptance-direction.md` の A002〜A004) |
| `tests/fixtures/sadf_sample.json` | `sadf -j` 出力の**再現**。実出力ではない (同ディレクトリの README.md 参照) |

## 配布

| パス | 概要 |
| --- | --- |
| `Dockerfile` | `python:3.12-slim` + sysstat 同梱。非 root・Uvicorn ワーカー 2 |
| `requirements.txt` | 実行時依存 (開発環境で検証したバージョンに固定) |
| `requirements-dev.txt` | テスト用の追加依存 |
