あなたはExecutor(実装担当)です。実施後は完了条件を確認し、停止条件に該当しない限り自動的に次のタスクへ進んでください。

# 【スプリントID】U004 — catalog-api

## タスク一覧(OKF副目次)

- [x] U004-T1 [ディレクトリ走査](#u004-t1-ディレクトリ走査) — 命名規則によるログファイルの列挙
- [x] U004-T2 [採取日の解決とキャッシュ](#u004-t2-採取日の解決とキャッシュ) — `sar`は1行目 / `sa`は`sadf -H`
- [x] U004-T3 [フィルタ・ソート・ページングとAPI](#u004-t3-フィルタソートページングとapi) — `GET /api/log-files`
- [x] U004-T4 [healthの件数接続](#u004-t4-healthの件数接続) — U001-T5 のダミー値を実値へ

---

## U004-T1: ディレクトリ走査

### 【目的】

* ログディレクトリ直下から対象ファイルを列挙する。

### 【作成・編集対象ファイル】

* `backend/app/services/__init__.py`, `backend/app/services/catalog_service.py`, `backend/tests/test_catalog_scan.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §6.1 (走査の表)

### 【実装内容】

* 対象は正規表現 `^sar?[0-9]{2}$` に合致する**通常ファイル**のみ。
* **直下のみ。サブディレクトリを再帰探索しない。**
* `kind` は名前が `sar` で始まれば `"sar"`、`sa` で始まれば `"sa"`。**判定順に注意** (`sar23` を `sa` と誤判定しない)。
* シンボリックリンクは `realpath` がログディレクトリ直下に解決される場合のみ対象とする。
* ディレクトリが存在しない場合は空リストを返す (例外にしない)。

### 【実装してはいけないこと】

* 採取日の読み取り (T2 の範囲)。

### 【Unit Test内容】

* `sa16` / `sar16` が対象になり、`sa1` / `sa123` / `saXX` / `foo` が対象外になること。
* `sar23` の `kind` が `"sar"`、`sa23` の `kind` が `"sa"` になること。
* サブディレクトリ内のファイルが列挙されないこと。
* 存在しないディレクトリで空リストが返ること。
* 実データディレクトリで 18 件 (`sa` 9 + `sar` 9) が列挙されること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_catalog_scan.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U004-T2: 採取日の解決とキャッシュ

### 【目的】

* ファイル内部から採取日を取得し、`(path, mtime, size)` をキーにキャッシュする (REQ-F-002, REQ-N-016)。

### 【作成・編集対象ファイル】

* `backend/app/services/catalog_service.py` (追記), `backend/tests/test_catalog_date.py`

### 【参照すべき仕様箇所】

* `docs/P003-backend-spec.md` §3.1 (キャッシュ失効判定), §6.2 (採取日の解決フロー)

### 【実装内容】

* `sar`: `read_header(path)` (U002-T2) を使う。**1 行目のみ読む。**
* `sa`: `sadf -H <path>` を実行し、出力から日付を抽出する ★FIXME★ (実出力を確認できていないため、複数の書式を試す実装にし、失敗しても例外にしない)
* キャッシュ: `dict[str, CatalogEntry]`。キーは絶対パス。`(mtime_ns, size)` が一致すればキャッシュを使う。
* 採取日を取得できなかったファイルは `unreadable` として計上し、**一覧から除外する**。例外にしない。
* `sadf` が無い場合、`sa` ファイルはすべて `unreadable` になる。**これは正常な動作である** (REQ-N-015)。

### 【実装してはいけないこと】

* 時間ベースの有効期限。

### 【Unit Test内容】

* `sar23` の採取日が `2026-08-23` になること。
* 2 回目の呼び出しで**ファイルが再オープンされないこと** (`read_header` をスパイして呼び出し回数で確認)。
* ファイルの `mtime` を変更するとキャッシュが失効し再読み取りされること (`tmp_path` にコピーして実施)。
* `size` が変わった場合も失効すること。
* `sadf` が無い環境で `sa` ファイルが `unreadable` に計上され、例外にならないこと。
* 日付を取得できないファイル (先頭行が壊れた `sar`) が一覧から除外されること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_catalog_date.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U004-T3: フィルタ・ソート・ページングとAPI

### 【目的】

* `GET /api/log-files` を完成させる。

### 【作成・編集対象ファイル】

* `backend/app/services/catalog_service.py` (追記), `backend/app/routers/log_files.py`, `backend/app/main.py` (ルータ登録), `backend/tests/test_log_files_api.py`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.2 (パラメータ・応答・エラー)
* `docs/P003-backend-spec.md` §6.3 (処理順), §6.4 (検証)

### 【実装内容】

* 処理順: 期間フィルタ (両端含む) → ソート `(date, kind順[sa=0,sar=1], fileName)` → `totalItems`/`totalPages` 算出 → 切り出し。
* `totalPages` は 0 件のとき **0**。
* `page` が総ページ数を超える場合は 200 かつ `items` 空。
* `fileId` は base64url(ファイル名) パディング除去 (`docs/P003-backend-spec.md` §5.1)。
* 検証: `from`/`to` 必須かつ `YYYY-MM-DD`、`from<=to`、`page>=1`、`1<=perPage<=100`。違反は `InvalidParameterError` (400)。

### 【実装してはいけないこと】

* `fileId` の**解決** (U005-T1 の範囲。ここでは生成のみ)。

### 【Unit Test内容】

* 期間内の `sa` と `sar` が両方返ること (REQ-F-017)。
* 並び順が日付昇順→`sa`→`sar` であること。
* 境界日 (`from` と同日 / `to` と同日) が含まれること。
* 1 ページ 10 件で `totalItems=18` / `totalPages=2` になること。
* 2 ページ目が 8 件になること。
* 0 件の期間で `totalPages=0` かつ `items` 空になること。
* `page=3` (超過) で 200 かつ `items` 空になること。
* `from` 欠落 / 形式不正 / `from>to` / `page=0` / `perPage=101` がいずれも 400 で `code="INVALID_PARAMETER"` になること。
* 応答フィールドが camelCase であること。

### 【実行コマンド】

* `python -m pytest backend/tests/test_log_files_api.py -q`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U004-T4: healthの件数接続

### 【目的】

* U001-T5 で 0 固定にした件数を実値へ接続する。

### 【作成・編集対象ファイル】

* `backend/app/routers/health.py`, `backend/tests/test_health.py` (追記)

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.5

### 【実装内容】

* `readableFileCount` = 採取日を取得できたファイル数、`unreadableFileCount` = 命名規則に合致するが採取日を取得できなかった数。
* U001-T5 に残したダミー値のコメントを削除する。

### 【Unit Test内容】

* 実データディレクトリで `readableFileCount + unreadableFileCount == 18` になること。
* `sadf` が無い環境で `sar` 9 件が readable、`sa` 9 件が unreadable になること。
* `sadfAvailable=False` でも `status="ok"` かつ 200 であること (REQ-N-015)。

### 【実行コマンド】

* `python -m pytest backend/tests -q` (2 回連続で同じ結果になることを確認する)

### 【完了条件】

* スプリント全体のテストが合格し、2 回連続で同じ結果になる。
* `docs/P007-impl-direction.md` の U004 行を `[x]` に更新する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

## 重要

* 各タスクの範囲外のファイルは編集しないでください。
* タスクの実装後、実行したテストコマンドと結果を報告してください。
* タスクが完了したら、上記「タスク一覧」の該当行を `[x]` に更新してください。
