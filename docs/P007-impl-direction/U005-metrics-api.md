あなたはExecutor(実装担当)です。実施後は完了条件を確認し、停止条件に該当しない限り自動的に次のタスクへ進んでください。

# 【スプリントID】U005 — metrics-api

## タスク一覧(OKF副目次)

- [x] U005-T1 [fileIdの解決](#u005-t1-fileidの解決) — パストラバーサル防止を含む検証順序
- [x] U005-T2 [メトリクスサービス](#u005-t2-メトリクスサービス) — リーダ選択・LRU・hint生成
- [x] U005-T3 [メトリクス取得API](#u005-t3-メトリクス取得api) — `GET /api/log-files/{fileId}/metrics`
- [x] U005-T4 [メトリクスカタログAPI](#u005-t4-メトリクスカタログapi) — `GET /api/metric-catalog`

---

## U005-T1: fileIdの解決

### 【目的】

* 不透明な `fileId` から実ファイルを安全に解決する (REQ-N-007)。

### 【作成・編集対象ファイル】

* `backend/app/services/metrics_service.py`, `backend/tests/test_fileid.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §5 (生成規則と解決手順のフロー図)

### 【実装内容】

* `encode_file_id(file_name) -> str`: base64url、パディング `=` 除去。
* `resolve_file_id(file_id, log_dir) -> Path`: **必ずこの順で検証する**。
  1. base64url として復号できるか (できなければ `FileNotFoundAppError`)
  2. 復号結果が `^sar?[0-9]{2}$` に合致するか (**パス結合より前**に行う)
  3. `log_dir / file_name` を結合
  4. `realpath` が `log_dir` 直下か
  5. 通常ファイルとして存在するか
* **失敗はすべて `FileNotFoundAppError` (404) に丸める。** 存在の有無を応答から区別できないようにする。

### 【実装してはいけないこと】

* 検証順序の変更 (正規表現検証をパス結合の後に行うこと)。

### 【Unit Test内容】

* `encode` → `resolve` の往復で元のファイルに解決されること。
* base64url として不正な文字列が 404 になること。
* `../../etc/passwd` を符号化した `fileId` が 404 になること。
* 絶対パス `/etc/passwd` を符号化した `fileId` が 404 になること。
* `sa1` / `sa123` / `README` など命名規則外が 404 になること。
* 存在しない `sa99` が 404 になること。
* ディレクトリ外を指すシンボリックリンクが 404 になること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_fileid.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U005-T2: メトリクスサービス

### 【目的】

* `kind` に応じてリーダを選び、結果をキャッシュし、`sa` 失敗時の `hint` を作る。

### 【作成・編集対象ファイル】

* `backend/app/services/metrics_service.py` (追記), `backend/tests/test_metrics_service.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §7.1 (処理フロー), §11.2 (`hint` 生成)

### 【実装内容】

* `get_metrics(file_id) -> MetricsResponse`。
* `kind == "sar"` → `read_sar_text`、`kind == "sa"` → `read_sa_binary`。**どちらも同じ `normalize()` に通す** (REQ-F-024)。
* LRU キャッシュ (最大 8)。キーは `(abs_path, mtime_ns, size)`。
* `SadfUnavailableError` / `SadfFailedError` を捕捉し、カタログサービスに**同一採取日の `sar` ファイル**が存在するか問い合わせる。存在すれば `hint` に名前を含めて再送出する。存在しなければ `hint=None`。
  * 例: `同一日の sar ファイル (sar23) が存在します。そちらを選択すると閲覧できます。`

### 【実装してはいけないこと】

* `sa` / `sar` それぞれに別の正規化を書くこと。

### 【Unit Test内容】

* `sar` の `fileId` で `MetricsResponse` が返り、`kind="sar"` であること。
* 2 回目の呼び出しでリーダが再実行されないこと (スパイで確認)。
* `mtime` 変更でキャッシュが失効すること。
* LRU が 9 件目で最古を追い出すこと。
* `sadf` 不在時に `SadfUnavailableError` が送出され、同日の `sar` があれば `hint` にその名前が含まれること。
* 同日の `sar` が無い場合に `hint=None` であること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_metrics_service.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U005-T3: メトリクス取得API

### 【目的】

* `GET /api/log-files/{fileId}/metrics` を公開する。

### 【作成・編集対象ファイル】

* `backend/app/routers/log_files.py` (追記), `backend/tests/test_metrics_api.py`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.3 (応答スキーマ・エラー表)

### 【実装内容】

* `MetricsResponse` をそのまま返す。
* 例外はハンドラ (U001-T2) が変換する。ルータで個別に握り潰さない。

### 【Unit Test内容】

* `sar23` の `fileId` で 200 が返り、`groups` が 21 件であること (P102 で PSI 3 グループを実データから発見したため 18 → 21)。
* すべての `series[].values` の長さが `timestamps` と一致すること。
* `timestamps` に `Average` を含む文字列が無いこと。
* `sa24` (収集途中) が 200 で返ること — `sadf` 不在環境では 503 になることを確認する。
* 未知の `fileId` が 404 / `FILE_NOT_FOUND` であること。
* `../` を含む `fileId` が 404 であること。
* `sadf` 不在環境で `sa` の `fileId` が 503 / `SADF_UNAVAILABLE` になり、`hint` に同日の `sar` 名が含まれること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_metrics_api.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U005-T4: メトリクスカタログAPI

### 【目的】

* `GET /api/metric-catalog` を公開する。

### 【作成・編集対象ファイル】

* `backend/app/routers/catalog.py`, `backend/app/main.py` (ルータ登録), `backend/tests/test_metric_catalog_api.py`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.4

### 【実装内容】

* `metrics/catalog.py` の `GROUP_DEF` / `METRIC_DEF` から応答を組む。`displayOrder` 順。

### 【Unit Test内容】

* 200 が返り、`groups` が 21 件であること。
* 順序が `displayOrder` に一致すること。
* 各グループに `title` と `description` が空でない値で存在すること。
* 各 `metrics[]` に `unit` フィールドが存在すること。
* `groups[].groupId` の集合が `GET /api/log-files/{sar23}/metrics` の `groupId` の集合を包含すること (カタログに無いグループが返らないこと)。

### 【実行コマンド】

* `python -m pytest backend/tests -q` (2 回連続で同じ結果になることを確認する)

### 【完了条件】

* スプリント全体のテストが合格し、2 回連続で同じ結果になる。
* `docs/P007-impl-direction.md` の U005 行を `[x]` に更新する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

## 重要

* 各タスクの範囲外のファイルは編集しないでください。
* タスクの実装後、実行したテストコマンドと結果を報告してください。
* タスクが完了したら、上記「タスク一覧」の該当行を `[x]` に更新してください。
