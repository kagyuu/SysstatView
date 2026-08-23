あなたはExecutor(実装担当)です。以下は1スプリント分の作業範囲と完了条件を定義したものです。実施後は、そのタスクの完了条件を満たしたことを確認したうえで、Executor Stepの「停止条件」に該当しない限り、自動的に次のタスクへ進んでください。人間の指示を待って停止しないでください。

# 【スプリントID】U001 — backend-foundation

## タスク一覧(OKF副目次)

- [x] U001-T1 [プロジェクト初期化と設定](#u001-t1-プロジェクト初期化と設定) — backend/ の骨格と `SYSSTAT_LOG_DIR`
- [x] U001-T2 [ドメイン例外とエラー応答](#u001-t2-ドメイン例外とエラー応答) — `AppError` 階層と例外ハンドラ
- [x] U001-T3 [Pydanticモデル](#u001-t3-pydanticモデル) — API 応答スキーマ
- [x] U001-T4 [メトリクス定義](#u001-t4-メトリクス定義) — 18グループ・指標・対応表
- [x] U001-T5 [構造化ログとhealth](#u001-t5-構造化ログとhealth) — JSON ログと `GET /api/health`

---

## U001-T1: プロジェクト初期化と設定

### 【目的】

* バックエンドのコード格納先を初期化し、以降のタスクが載る土台を作る。

### 【作成・編集対象ファイル】

* `backend/pyproject.toml`, `backend/requirements.txt`
* `backend/app/__init__.py`, `backend/app/config.py`, `backend/app/main.py`
* `backend/tests/__init__.py`, `backend/tests/conftest.py`

### 【参照すべき仕様箇所】

* `docs/P005-impl-plan.md` §1.2 (バージョン), §1.3 (ディレクトリ構成)
* `docs/P003-backend-spec.md` §6.1 (`SYSSTAT_LOG_DIR`)

### 【実装内容】

* コード格納先 `backend/` がまだ初期化されていないため、**このタスクで初期化する**。`pip` + `requirements.txt` 相当の構成で初期化する (仮想環境は作らず、実行環境の Python を用いる)。
* 依存: `fastapi`, `uvicorn[standard]`, `pydantic`, `pytest`, `httpx`。
* `config.py`: 環境変数 `SYSSTAT_LOG_DIR` (既定 `/var/log/sysstat`) を読む `Settings` を提供する。テストから差し替えられるよう、モジュール変数ではなく**関数または依存性注入**で取得できる形にする。
* `main.py`: `create_app()` で `FastAPI` インスタンスを生成する。ルータ登録は後続タスクで行う。
* `tests/conftest.py`: 実データのパス (`sysstat-log/var/log/sysstat`) を返す fixture `real_log_dir` を定義する。

### 【実装してはいけないこと】

* ルータ・サービス・リーダの実装 (T2 以降および U002 以降の範囲)。
* CORS ミドルウェアの追加 (`docs/P003-backend-spec.md` §2 により**実装しない**)。

### 【Unit Test内容】

* `SYSSTAT_LOG_DIR` 未設定時に既定値が返ること。
* 環境変数を設定した場合にその値が返ること。
* `create_app()` が `FastAPI` インスタンスを返すこと。

### 【実行コマンド】

* `python -m pytest backend/tests -q`

### 【完了条件】

* 上記テストがすべて合格する。
* `python -c "from backend.app.main import create_app; create_app()"` が例外なく完了する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U001-T2: ドメイン例外とエラー応答

### 【目的】

* リーダ層・サービス層が HTTP を知らずにエラーを表現できるようにする。

### 【作成・編集対象ファイル】

* `backend/app/errors.py`, `backend/app/main.py` (ハンドラ登録), `backend/tests/test_errors.py`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.1 (エラー応答の形式とコード表)
* `docs/P003-backend-spec.md` §11.1 (例外と HTTP の対応)

### 【実装内容】

* 基底 `AppError(Exception)` に `code` / `http_status` / `message` / `detail` / `hint` を持たせる。
* 派生: `InvalidParameterError`(400), `FileNotFoundAppError`(404), `UnsupportedFileError`(422), `ParseFailedError`(422), `SadfUnavailableError`(503), `SadfFailedError`(502)。
* `create_app()` に例外ハンドラを登録し、`{"error": {...}}` 形式の JSON を返す。
* 未捕捉の例外は `INTERNAL_ERROR` (500) に変換する。**`detail` に例外の文字列表現を含めない。** ログにはスタックトレースを記録する。
* FastAPI の `RequestValidationError` も `INVALID_PARAMETER` (400) に変換し、同じ形式で返す。

### 【実装してはいけないこと】

* 具体的なエンドポイントの実装。

### 【Unit Test内容】

* 各例外クラスが仕様どおりの `code` と `http_status` を持つこと。
* ハンドラが `{"error": {"code", "message", "detail", "hint"}}` の形で返すこと。
* 未捕捉例外が 500 / `INTERNAL_ERROR` になり、応答の `detail` に元の例外メッセージが含まれないこと。

### 【実行コマンド】

* `python -m pytest backend/tests/test_errors.py -q`

### 【完了条件】

* 上記テストがすべて合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U001-T3: Pydanticモデル

### 【目的】

* API 応答スキーマを型として定義し、以降のタスクが参照できるようにする。

### 【作成・編集対象ファイル】

* `backend/app/models.py`, `backend/tests/test_models.py`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.2〜§5.5 (各応答の形)
* `docs/P003-backend-spec.md` §4.2 (Python の型)

### 【実装内容】

* `LogFileInfo`, `LogFileListResponse`, `Series`, `MetricGroup`, `MetricsResponse`, `MetricDefInfo`, `GroupDefInfo`, `MetricCatalogResponse`, `HealthResponse`, `ErrorBody`, `ErrorResponse`。
* **フィールド名は camelCase で直接定義する** (`fileId`, `sizeBytes`, `keyLabel`, `cpuCount` など)。
* `date` は `datetime.date`、`timestamps` は `list[str]`。

### 【実装してはいけないこと】

* モデルにビジネスロジック (解析・集計) を持たせること。

### 【Unit Test内容】

* 各モデルが仕様どおりのフィールド名で JSON 直列化されること (camelCase であること)。
* `Series.values` に `None` を含められること。
* 必須フィールドの欠落でバリデーションエラーになること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_models.py -q`

### 【完了条件】

* 上記テストがすべて合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U001-T4: メトリクス定義

### 【目的】

* 18 メトリクスグループの定義と、`sar` 列名・`sadf` キーからグループを判定する対応表を、**単一の場所**に用意する。以降のすべてのモジュールがこれを参照する。

### 【作成・編集対象ファイル】

* `backend/app/metrics/__init__.py`, `backend/app/metrics/catalog.py`, `backend/tests/test_catalog_def.py`

### 【参照すべき仕様箇所】

* `docs/P001-requirement.md` §7 (18 グループの一覧・説明文の元)
* `docs/P003-backend-spec.md` §9.3 (対応表), §10 (単位割り当て規則)

### 【実装内容】

* `GroupDef`: `groupId` / `title` / `description` / `keyLabel` / `displayOrder`。18 件を `displayOrder` 順に定義する。
* `MetricDef`: `name` / `groupId` / `unit` / `description`。`docs/P001-requirement.md` §7 の主な指標を網羅する。
* `unit_for(column_name)`: §10 の規則 (`%` 始まり→`%`、`kb` 始まり→`KB`、`kB/s` 終わり→`KB/s`、`/s` 終わり→`/s`、`await`→`ms`、その他→`None`)。**判定順に注意する** (`%` と `kb` の判定を `/s` より先に行う)。
* `identify_group_from_sar(columns, key_label)`: 列名の集合とキー列見出しから `groupId` を返す。§9.3 の識別列にもとづく。**列の並び順・個数に依存しない。**
* `SADF_KEY_TO_GROUP`: `sadf` の統計種別キー → `groupId` の対応。
* `SADF_FIELD_TO_METRIC`: `sadf` のフィールド名 → `sar` 表記の指標名 (例: `user` → `%usr`)。**指標名は `sar` 表記に揃える。**

### 【実装してはいけないこと】

* 対応表を他モジュールにも持たせること (定義を 2 箇所に分けない)。

### 【Unit Test内容】

* 21 グループが定義され、`displayOrder` に重複が無いこと。
* `MetricDef` の `groupId` がすべて `GroupDef` に存在すること。
* `unit_for` が `%usr`→`%`, `kbmemfree`→`KB`, `rxkB/s`→`KB/s`, `proc/s`→`/s`, `await`→`ms`, `ldavg-1`→`None` を返すこと。
* `identify_group_from_sar` が、`MG-NET` と `MG-NETERR` (どちらも `IFACE` キー) を識別列で正しく区別すること。
* `identify_group_from_sar` が、列順を入れ替えても同じ結果を返すこと。
* `SADF_KEY_TO_GROUP` の値がすべて `GroupDef` に存在すること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_catalog_def.py -q`

### 【完了条件】

* 上記テストがすべて合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U001-T5: 構造化ログとhealth

### 【目的】

* 標準出力への JSON ログを構成し、`GET /api/health` を骨格として提供する。

### 【作成・編集対象ファイル】

* `backend/app/logging_setup.py`, `backend/app/routers/__init__.py`, `backend/app/routers/health.py`
* `backend/app/main.py` (ルータ・ミドルウェア登録), `backend/tests/test_health.py`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.5 (health の応答)
* `docs/P003-backend-spec.md` §12 (ログ出力)

### 【実装内容】

* `logging_setup.py`: 1 行 1 JSON のフォーマッタを標準出力ハンドラに設定する。必須フィールド `ts` / `level` / `event` / `message`。追加フィールドを `extra` で載せられるようにする。
* リクエストログ用のミドルウェアを `create_app()` に登録し、`method` / `path` / `status` / `durationMs` を記録する。
* `routers/health.py`: `GET /api/health` を実装する。
  * `logDir` は設定値。
  * `sadfAvailable` は `shutil.which("sadf")` の有無で判定し、あれば `sadf -V` からバージョンを取得する。取得失敗時は `sadfVersion=None` とする。
  * `readableFileCount` / `unreadableFileCount` は **このスプリントでは 0 固定**とし、U004-T4 で実値に接続する。その旨をコード中のコメントに明記する。
* `sadf` が無くても `status="ok"` を返す (REQ-N-015)。

### 【実装してはいけないこと】

* ログディレクトリの走査 (U004 の範囲)。

### 【Unit Test内容】

* ログフォーマッタの出力が 1 行の JSON として解釈でき、必須フィールドを持つこと。
* `GET /api/health` が 200 を返し、`status="ok"` であること。
* `sadf` が無い環境で `sadfAvailable=False` / `sadfVersion=None` かつ 200 / `status="ok"` であること。
* `shutil.which` をモックして `sadf` 有りの場合も 200 になること。

### 【実行コマンド】

* `python -m pytest backend/tests -q`

### 【完了条件】

* スプリント U001 の全単体テストが合格する。
* `docs/P007-impl-direction.md` の U001 行を `[x]` に更新する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

## 重要

* 各タスクの範囲外のファイルは編集しないでください。
* タスクの実装後、実行したテストコマンドと結果を報告してください。
* タスクが完了したら、上記「タスク一覧」の該当行を `[x]` に更新してください。
* 全タスクが完了したら、`docs/P007-impl-direction.md` の本スプリント行を `[x]` に更新してください。
