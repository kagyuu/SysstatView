あなたはExecutor(実装担当)です。実施後は完了条件を確認し、停止条件に該当しない限り自動的に次のタスクへ進んでください。

# 【スプリントID】U006 — frontend-foundation-sc01

## タスク一覧(OKF副目次)

- [x] U006-T1 [Angularプロジェクト初期化](#u006-t1-angularプロジェクト初期化) — 骨格・ルーティング・開発プロキシ
- [x] U006-T2 [型定義とAPIクライアント](#u006-t2-型定義とapiクライアント) — `ApiService`
- [x] U006-T3 [状態保持サービス](#u006-t3-状態保持サービス) — `SearchStateService`
- [x] U006-T4 [SC-01コンポーネント](#u006-t4-sc-01コンポーネント) — 検索エリアと一覧エリア
- [x] U006-T5 [SC-01の単体テスト](#u006-t5-sc-01の単体テスト) — 初期値・ページング・選択

---

## U006-T1: Angularプロジェクト初期化

### 【目的】

* フロントエンドのコード格納先を初期化する。

### 【作成・編集対象ファイル】

* `frontend/` 一式 (`package.json`, `angular.json`, `tsconfig*.json`, `src/`)
* `frontend/proxy.conf.json`

### 【参照すべき仕様箇所】

* `docs/P005-impl-plan.md` §1.2 (Angular 18 系), §1.3 (ディレクトリ構成)
* `docs/P003-backend-spec.md` §2 (同一オリジン方針)

### 【実装内容】

* `frontend/` がまだ初期化されていないため、**このタスクで初期化する**。`ng new` 相当の構成 (スタンドアロンコンポーネント、ルーティング有効、SCSS) で初期化する。
* ルーティング: `''` → SC-01、`'graph/:fileId'` → SC-02 (SC-02 は U007 で実装するため、ここではプレースホルダで可)。
* `proxy.conf.json`: `/api` を `http://localhost:8000` へ転送する。`angular.json` の serve 設定に紐付ける。
* **CORS 設定・絶対 URL のベースパスを持たせない。** API は常に相対パス `/api/...` で呼ぶ。

### 【実装してはいけないこと】

* SC-02 の中身の実装 (U007 の範囲)。

### 【Unit Test内容】

* アプリケーションのルートコンポーネントが生成できること。
* ルーティング定義に `''` と `graph/:fileId` が含まれること。

### 【実行コマンド】

* `npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless`

### 【完了条件】

* 上記テストが合格し、`npm --prefix frontend run build` が成功する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U006-T2: 型定義とAPIクライアント

### 【目的】

* バックエンドの応答スキーマに対応する型と、それを取得する `ApiService` を用意する。

### 【作成・編集対象ファイル】

* `frontend/src/app/models/*.ts`, `frontend/src/app/core/api.service.ts`, `frontend/src/app/core/api.service.spec.ts`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §5.1〜§5.5 (応答スキーマとエラー形式)

### 【実装内容】

* 型: `LogFileInfo`, `LogFileListResponse`, `Series`, `MetricGroup`, `MetricsResponse`, `MetricCatalogResponse`, `ApiError`。**バックエンドと同じ camelCase。**
* `ApiService`: `listLogFiles(from, to, page, perPage)`, `getMetrics(fileId)`, `getMetricCatalog()`, `getHealth()`。
* エラー応答 (`{error: {...}}`) を `ApiError` に変換して投げ直す。ネットワークエラーは `message="バックエンドに接続できません"` に変換する。

### 【Unit Test内容】

* `listLogFiles` が正しいクエリパラメータで `/api/log-files` を呼ぶこと (`HttpTestingController`)。
* 400 応答が `ApiError` に変換され `code` と `message` を持つこと。
* ネットワークエラーが規定のメッセージになること。

### 【実行コマンド】

* `npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U006-T3: 状態保持サービス

### 【目的】

* SC-02 へ遷移して戻っても SC-01 の状態が失われないようにする (REQ-F-014)。

### 【作成・編集対象ファイル】

* `frontend/src/app/core/search-state.service.ts`, `.spec.ts`

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §1.1 (状態管理), §4.1 (戻り時にAPIを再実行しない)

### 【実装内容】

* アプリケーションスコープ (`providedIn: 'root'`) で保持する。
* 保持する内容: `from` / `to` / `items` / `page` / `perPage` / `totalItems` / `totalPages` / `selectedFileId`。
* `hasState()` / `save(state)` / `restore()` を提供する。
* **`localStorage` / `sessionStorage` を使わない** (P002 §1.1 でリロード耐性は不要と決定済み)。

### 【Unit Test内容】

* 保存した状態がそのまま復元されること。
* 未保存のとき `hasState()` が `false` を返すこと。
* 復元後に元の値を書き換えても保持内容が変わらないこと (参照の共有をしていないこと)。

### 【実行コマンド】

* `npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless`

### 【完了条件】

* 上記テストが合格する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

---

## U006-T4: SC-01コンポーネント

### 【目的】

* ログファイル検索・選択画面を実装する。

### 【作成・編集対象ファイル】

* `frontend/src/app/pages/file-search/*` (component / template / style)

### 【参照すべき仕様箇所】

* `docs/P002-frontend-spec.md` §2 (レイアウト・バリデーション・一覧仕様・ページリンク・操作)

### 【実装内容】

* 上段: 開始日・終了日 (`<input type="date">`)、検索ボタン。初期値は**実行月の 1 日と末日**。
* 相関バリデーション `from <= to`。違反時はメッセージを出し **API を呼ばない**。
* 下段: ラジオボタン / ファイル名 / 種別 / 採取日 のテーブル。1 ページ 10 件。
* ページリンク `<前へ 1 2 3 4 次へ>`。**全ページ番号を表示する。`…` による省略表示を行わない** (P002 §2.3 の ★ACCEPTED★ 済みの決定)。現在ページはリンクにせず強調。1 ページ目で「前へ」、最終ページで「次へ」を非活性。総ページ数が 1 でも領域を表示する — 注: P011 影響分析 #2 にもとづく修正
* 初期選択は**表示中ページの先頭行**。ページ切り替え時も切り替え先の先頭行。
* 検索実行時は `page=1` に戻す。
* 0 件時: 「該当するログファイルがありません」を表示し、テーブルとページリンクを出さず、表示ボタンを非活性。
* 表示ボタン: `/graph/:fileId` へ遷移する前に `SearchStateService.save()` を呼ぶ。
* 画面初期表示時: `SearchStateService.hasState()` が `true` なら**復元し API を呼ばない**。`false` なら実行月の期間で検索する。
* ローディング中は操作ボタンを非活性にする。エラー時は `message` (と `hint`) を表示する。

### 【実装してはいけないこと】

* グラフ描画 (U007 の範囲)。

### 【Unit Test内容】

* T5 でまとめて実施する。

### 【実行コマンド】

* `npm --prefix frontend run build`

### 【完了条件】

* ビルドが成功する。

### 【次タスクに進む前の停止条件】

* 3回自己修正してもビルドが通らない場合。

---

## U006-T5: SC-01の単体テスト

### 【目的】

* SC-01 の画面挙動を検証する。

### 【作成・編集対象ファイル】

* `frontend/src/app/pages/file-search/file-search.component.spec.ts`

### 【参照すべき仕様箇所】

* `docs/P006-test-plan.md` §3.3 (フロントエンド単体の観点)

### 【実装内容】

* 現在日を固定して注入できるようにし、実行月の算出を検証する。

### 【Unit Test内容】

* 初期値が実行月の 1 日と末日になること。**うるう年 (2024-02 → 29 日)、平年 2 月 (2025-02 → 28 日)、31 日月、30 日月**を検証する。
* `from > to` でメッセージが出て API が呼ばれないこと。
* 一覧が 10 件ごとに表示されること。
* 初期選択が先頭行であること。
* ページ切り替え後も先頭行が選択されること。
* 検索実行で `page=1` に戻ること。
* 0 件時にテーブルが非表示で表示ボタンが非活性であること。
* 1 ページ目で「前へ」、最終ページで「次へ」が非活性であること。
* **総ページ数が 12 のとき、ページ番号リンクが 12 個すべて表示され、`…` が現れないこと** — 注: P011 影響分析 #2 にもとづく追加
* 保持状態がある場合、初期表示で API を呼ばず復元すること。

### 【実行コマンド】

* `npm --prefix frontend test -- --watch=false --browsers=ChromeHeadless` (2 回連続で同じ結果になることを確認する)

### 【完了条件】

* 上記テストがすべて合格し、2 回連続で同じ結果になる。
* `docs/P007-impl-direction.md` の U006 行を `[x]` に更新する。

### 【次タスクに進む前の停止条件】

* 3回自己修正しても単体テストが合格しない場合。

## 重要

* 各タスクの範囲外のファイルは編集しないでください。
* タスクの実装後、実行したテストコマンドと結果を報告してください。
* タスクが完了したら、上記「タスク一覧」の該当行を `[x]` に更新してください。
