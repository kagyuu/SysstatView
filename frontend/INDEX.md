# frontend/ 実装構造の目次

Angular 20 の SPA。2 画面 (ログファイル検索・選択 / グラフ表示)。

* 設計: `docs/P002-frontend-spec.md` / 決定の理由: `docs/ADR.md`
* 開発起動: `npm start` (`/api` は `proxy.conf.json` で `localhost:8000` へ転送)
* テスト: `npm test` / ビルド: `npm run build`

## アプリ骨格

| パス | 概要 |
| --- | --- |
| `src/app/app.ts` / `app.html` / `app.scss` | ルートコンポーネント (ヘッダと `router-outlet`) |
| `src/app/app.routes.ts` | `''` → SC-01、`graph/:fileId` → SC-02。いずれも遅延読み込み |
| `src/app/app.config.ts` | ルータと HttpClient の登録 |

## 共通 (core)

| パス | 概要 |
| --- | --- |
| `src/app/core/api.service.ts` | API クライアント。**常に相対パス**で呼ぶ (ADR-001)。エラー応答を `ApiError` に変換する |
| `src/app/core/search-state.service.ts` | SC-01 の状態保持。SC-02 から戻ったときの復元に使う (REQ-F-014) |
| `src/app/core/current-date.ts` | 「実行月」の算出。テストから現在日を注入できる |
| `src/app/models/api.models.ts` | バックエンド応答に対応する型 (camelCase) と `ApiError` |

## 画面

| パス | 概要 |
| --- | --- |
| `src/app/pages/file-search/` | **SC-01**。期間検索・1 ページ 10 件・ラジオ単一選択・全ページ番号のページリンク・0 件表示 |
| `src/app/pages/graph-view/graph-view.component.ts` | **SC-02**。カタログとメトリクスを取得し、Chart.js で描画。`IntersectionObserver` による遅延描画 |
| `src/app/pages/graph-view/chart-builder.ts` | メトリクスグループを**単位ごとのグラフ**に分割する (P002 §3.4)。時刻を epoch ミリ秒に変換 (ADR-006) |

## テスト

| パス | 概要 |
| --- | --- |
| `src/app/pages/file-search/file-search.component.spec.ts` | 初期値 (うるう年含む)・バリデーション・ページング・選択・状態復元 |
| `src/app/pages/graph-view/chart-builder.spec.ts` | 単位別分割・系列名・順序の安定性・X 値が実時間差に比例すること |
| `src/app/pages/graph-view/graph-view.component.spec.ts` | 表示項目・見出しと説明の順序・エラー表示・戻る |
| `src/app/core/*.spec.ts` | API クライアントと状態保持サービス |

## 配布

| パス | 概要 |
| --- | --- |
| `proxy.conf.json` | 開発時に `/api` をバックエンドへ転送し、同一オリジンに見せる |
| `nginx.conf` | 本番の静的配信 + `/api/` のリバースプロキシ + SPA フォールバック |
| `Dockerfile` | `node:22-alpine` でビルド → `nginx:alpine` で配信 |
